from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os
import json

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Permissions,PermissionRoleMap
from app.core.security import oauth2_scheme
from app.models.sqlalchemy_schemas.authentication import BlacklistedTokens
from app.services.authentication_service.authentication_core import _hash_token
from app.models.sqlalchemy_schemas.roles import Roles
from app.core.redis_manager import redis

load_dotenv()

# =========================
# JWT ENV CONFIGS
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))


# ======================================================
# 1️⃣ Extract current user from JWT
# ======================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the current user from JWT access token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id= payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id=int(user_id)
    except JWTError:    
        raise credentials_exception

    # Fetch user by ID
    result = await db.execute(select(Users).where(Users.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise credentials_exception

    # Check token blacklist (protect against revoked tokens)
    try:
        token_hash = _hash_token(token)
        blk_result = await db.execute(
            select(BlacklistedTokens).where(BlacklistedTokens.token_value_hash == token_hash)
        )
        blk = blk_result.scalars().first()
        if blk:
            raise credentials_exception
    except Exception:
        # Any failure in blacklist check should not leak details; if DB check fails, deny
        raise credentials_exception

    return user


# ======================================================
# 2️⃣ Extract permissions for the current user
# ======================================================
async def get_user_permissions(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extracts all permissions for the current user via their role with Redis caching.
    
    Retrieves user permissions from Redis cache first. If not cached, queries database,
    builds permission map, and stores in Redis with 1-hour TTL (3600 seconds).
    
    Returns -> dict[resource_name: set(permission_types)]
    
    Side Effects:
        - Queries database if cache miss (queries permissions by role_id).
        - Caches result in Redis with key: `user_perms:{role_id}` TTL 3600 seconds.
        - Normalizes resource and permission_type to uppercase strings.
    
    Raises:
        HTTPException (403): If user has no role_id assigned.
    """

    # Step 1: Validate role_id
    role_id = current_user.role_id
    if not role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not found for permission mapping",
        )

    # Step 2: Check Redis cache first
    cache_key = f"user_perms:{role_id}"
    permissions_map = None
    
    try:
        if redis:
            cached_data = await redis.get(cache_key)
            if cached_data:
                # Convert cached JSON back to dict with sets
                cached_dict = json.loads(cached_data)
                permissions_map = {k: set(v) for k, v in cached_dict.items()}
    except Exception as e:
        # Log error but continue - cache miss should not block request
        print(f"⚠️  Redis cache retrieval failed: {e}")
        pass

    # Step 3: If not in cache, query database
    if not permissions_map:
        result = await db.execute(
            select(Permissions.resource, Permissions.permission_type)
            .join(PermissionRoleMap, PermissionRoleMap.permission_id == Permissions.permission_id)
            .where(PermissionRoleMap.role_id == role_id)
        )

        records = result.all()

        # Step 4: Build a permission map
        # Normalize to plain uppercase strings for both resource and permission type so route checks
        # can safely compare against enum.value (which are uppercase strings in this project).
        permissions_map = {}
        for resource, perm_type in records:
            # resource and perm_type may be Enum members or plain strings depending on driver; normalize
            if hasattr(resource, "value"):
                resource_key = str(resource.value).upper()
            else:
                resource_key = str(resource).upper()

            if hasattr(perm_type, "value"):
                perm_key = str(perm_type.value).upper()
            else:
                perm_key = str(perm_type).upper()

            permissions_map.setdefault(resource_key, set()).add(perm_key)

        # Step 5: Cache in Redis (convert sets to lists for JSON serialization)
        try:
            if redis and permissions_map:
                cache_data = {k: list(v) for k, v in permissions_map.items()}
                await redis.setex(cache_key, 3600, json.dumps(cache_data))  # 1-hour TTL
        except Exception as e:
            # Cache write failure should not block request
            print(f"⚠️  Redis cache storage failed: {e}")
            pass

    # Step 6: Return empty map if no permissions found
    if not permissions_map:
        return {}

    return permissions_map


# ======================================================
# 3️⃣ Invalidate permissions cache (called when permissions change)
# ======================================================
async def invalidate_permissions_cache(role_id: int):
    """
    Invalidate the permissions cache for a specific role.
    
    Called when permissions are assigned/revoked for a role to ensure all users
    with that role fetch fresh permissions on next request.
    
    Args:
        role_id (int): The role ID whose permissions were modified.
    
    Side Effects:
        - Deletes Redis cache key: `user_perms:{role_id}`.
        - Silently ignores Redis errors (cache invalidation failure non-blocking).
    """
    cache_key = f"user_perms:{role_id}"
    
    try:
        if redis:
            await redis.delete(cache_key)
            print(f"✅ Invalidated permission cache for role_id={role_id}")
    except Exception as e:
        # Cache invalidation failure should not block response
        print(f"⚠️  Redis cache invalidation failed for role_id={role_id}: {e}")
        pass


async def invalidate_all_permissions_cache():
    """
    Invalidate all permissions caches (all roles).
    
    Called during system-wide permission changes. Clears all keys matching pattern:
    `user_perms:*` from Redis.
    
    Side Effects:
        - Scans Redis for all `user_perms:*` keys and deletes them.
        - Silently ignores Redis errors.
    """
    try:
        if redis:
            # Use SCAN to iterate keys matching pattern (non-blocking)
            cursor = 0
            pattern = "user_perms:*"
            deleted_count = 0
            
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted_count += len(keys)
                
                if cursor == 0:
                    break
            
            print(f"✅ Invalidated all permission caches ({deleted_count} keys deleted)")
    except Exception as e:
        # Cache invalidation failure should not block response
        print(f"⚠️  Redis cache invalidation failed: {e}")
        pass


async def ensure_not_basic_user(current_user: Users = Depends(get_current_user)):
    """Dependency that rejects requests coming from the basic 'user' role (role_id == 1).

    Use this dependency on routes or routers that must not be accessible to regular users.
    """
    if getattr(current_user, "role_id", None) == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges: action not available for basic users",
        )
    return True


async def ensure_only_basic_user(current_user: Users = Depends(get_current_user)):
    """Dependency that permits only users with the basic 'customer' role (role_id == 1).

    Use this dependency on routes that should only be accessible to regular/basic users.
    """
    if getattr(current_user, "role_id", None) != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is only available for basic users",
        )
    return True


async def ensure_admin(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Dependency that permits only users whose role name is 'ADMIN'.

    This queries the `roles_utility` table to verify the human-readable role name.
    """
    role_id = getattr(current_user, "role_id", None)
    if not role_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")

    result = await db.execute(select(Roles).where(Roles.role_id == role_id))
    role = result.scalars().first()
    if not role or not getattr(role, "role_name", "").upper() == "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return True
