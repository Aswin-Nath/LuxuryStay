from fastapi import Depends, HTTPException, status, Security
from fastapi.security import SecurityScopes
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
# 1.5️⃣ Check permissions using SecurityScopes (Resource:permission format)
# ======================================================

async def check_permission(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate JWT, check blacklist, verify user's role and permissions against required scopes.
    Permissions follow "RESOURCE:PERMISSION" format.
    """

    # --- Token validation
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub") or 0)
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # --- User validation
    user = (await db.execute(select(Users).where(Users.user_id == user_id))).scalars().first()
    if not user:
        raise credentials_exception

    # --- Token blacklist check
    token_hash = _hash_token(token)
    if (await db.execute(
        select(BlacklistedTokens).where(BlacklistedTokens.token_value_hash == token_hash)
    )).scalars().first():
        raise credentials_exception

    # --- Role validation
    role = (await db.execute(select(Roles).where(Roles.role_id == user.role_id))).scalars().first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # --- Permissions fetch & flatten
    permissions_result = await db.execute(
        select(Permissions.permission_name)
        .join(PermissionRoleMap, PermissionRoleMap.permission_id == Permissions.permission_id)
        .where(PermissionRoleMap.role_id == user.role_id)
    )

    # Flatten tuple results like [('X',), ('Y',)] → ['X', 'Y']
    user_permissions = [perm[0].upper() for perm in permissions_result.all()]
    # --- Permission check
    for scope in security_scopes.scopes:
        if scope.upper() not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: insufficient privileges"
            )

    return payload

# ======================================================
# 2️⃣ Extract permissions for the current user

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
