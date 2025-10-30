from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os

from app.database.postgres_connection import get_db
from app.models.orm.users import Users
from app.models.orm.permissions import Permissions,PermissionRoleMap
from app.core.security import oauth2_scheme

load_dotenv()

# =========================
# JWT ENV CONFIGS
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


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
    permissions_map = {}
    for resource, perm_type in records:
        permissions_map.setdefault(resource, set()).add(perm_type)

    # Step 4: Return empty map if no permissions found
    if not permissions_map:
        return {}

    return permissions_map
