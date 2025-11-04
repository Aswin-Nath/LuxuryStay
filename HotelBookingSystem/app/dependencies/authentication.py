from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Permissions,PermissionRoleMap
from app.core.security import oauth2_scheme
from app.models.sqlalchemy_schemas.authentication import BlacklistedTokens
from app.services.authentication_service.auth import _hash_token

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
    Extracts all permissions for the current user via their role.
    Returns -> dict[resource_name: set(permission_types)]
    """

    # Step 1: Validate role_id
    role_id = current_user.role_id
    if not role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not found for permission mapping",
        )

    # Step 2: Join role-permission map with permissions table
    result = await db.execute(
        select(Permissions.resource, Permissions.permission_type)
        .join(PermissionRoleMap, PermissionRoleMap.permission_id == Permissions.permission_id)
        .where(PermissionRoleMap.role_id == role_id)
    )

    records = result.all()

    # Step 3: Build a permission map
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

    # Step 4: Return empty map if no permissions found
    if not permissions_map:
        return {}

    return permissions_map


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
