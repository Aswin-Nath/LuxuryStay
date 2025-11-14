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
from app.utils.authentication_util import _hash_token
from app.models.sqlalchemy_schemas.roles import Roles
from app.core.redis_manager import redis
from app.core.cache import get_cached, set_cached

load_dotenv()

# =========================
# JWT ENV CONFIGS
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))


# ======================================================
# 1️⃣ Extract current user from JWT
# ======================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the current user from JWT access token.
    
    Validates:
    1. JWT token signature and expiration
    2. User exists in database
    3. Token is not blacklisted (by session_id)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id = int(user_id)
    except JWTError:    
        raise credentials_exception

    # Fetch user by ID
    result = await db.execute(select(Users).where(Users.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise credentials_exception

    # Check if user's session is blacklisted (verify by session_id lookup)
    try:
        from app.crud.authentication import get_session_by_user_id
        
        session = await get_session_by_user_id(db, user_id)
        if not session:
            raise credentials_exception
        
        # Check if this session is blacklisted
        blk_result = await db.execute(
            select(BlacklistedTokens).where(BlacklistedTokens.session_id == session.session_id)
        )
        blk = blk_result.scalars().first()
        if blk:
            raise credentials_exception
            
    except HTTPException:
        raise
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
    
    Validates:
    1. JWT token signature and expiration
    2. User exists in database
    3. Session is not blacklisted (by session_id)
    4. User has required permissions
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

    # --- Session blacklist check (using session_id instead of token_hash)
    try:
        from app.crud.authentication import get_session_by_user_id
        
        session = await get_session_by_user_id(db, user_id)
        if not session:
            raise credentials_exception
        
        # Check if this session is blacklisted
        if (await db.execute(
            select(BlacklistedTokens).where(BlacklistedTokens.session_id == session.session_id)
        )).scalars().first():
            raise credentials_exception
            
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

    # --- Role validation
    role = (await db.execute(select(Roles).where(Roles.role_id == user.role_id))).scalars().first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # --- Permissions fetch & flatten with caching
    # Check cache first using role_id as key
    cache_key = f"user_perms:{user.role_id}"
    cached_permissions = await get_cached(cache_key)
    
    if cached_permissions is not None:
        # Use cached permissions
        user_permissions = cached_permissions
    else:
        # Query permissions from database
        permissions_result = await db.execute(
            select(Permissions.permission_name)
            .join(PermissionRoleMap, PermissionRoleMap.permission_id == Permissions.permission_id)
            .where(PermissionRoleMap.role_id == user.role_id)
        )

        # Flatten tuple results like [('X',), ('Y',)] → ['X', 'Y']
        user_permissions = [perm[0].upper() for perm in permissions_result.all()]
        
        # Cache permissions for this role with 300-second TTL
        await set_cached(cache_key, user_permissions, ttl=300)
    
    # --- Permission and Role Scope check
    for scope in security_scopes.scopes:
        scope_upper = scope.upper()
        user_role_name_upper = role.role_name.upper()
        
        # Check if scope is a known role type:
        # "CUSTOMER" = exact match with "customer" role
        # "ADMIN" = matches any role containing "admin" (super_admin, normal_admin, content_admin, BACKUP_ADMIN)
        
        if scope_upper == "CUSTOMER":
            # Check if user's role_name is exactly "customer"
            if user_role_name_upper != "CUSTOMER":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: requires CUSTOMER role"
                )
        elif scope_upper == "ADMIN":
            # Check if user's role_name contains "admin" (any admin role)
            if "ADMIN" not in user_role_name_upper:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: requires ADMIN role"
                )
        else:
            # This is a permission check (not a role)
            if scope_upper not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: insufficient privileges"
                )

    return payload


