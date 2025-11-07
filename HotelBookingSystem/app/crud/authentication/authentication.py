from datetime import datetime
from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.authentication import Sessions


# ==========================================================
# 🔹 USER CRUD
# ==========================================================

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[Users]:
    """Fetch a user by email."""
    result = await db.execute(select(Users).where(Users.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Users]:
    """Fetch a user by user_id."""
    result = await db.execute(select(Users).where(Users.user_id == user_id))
    return result.scalars().first()


async def create_user_record(
    db: AsyncSession,
    full_name: str,
    email: str,
    password_hash: str,
    phone_number: Optional[str],
    role_id: int,
    status_id: int,
    created_by: Optional[int] = None,
) -> Users:
    """Insert a new user record."""
    user_obj = Users(
        full_name=full_name,
        email=email,
        password=password_hash,
        phone_number=phone_number,
        role_id=role_id,
        status_id=status_id,
        created_by=created_by,
    )
    db.add(user_obj)
    await db.flush()
    await db.refresh(user_obj)
    return user_obj


async def update_user_password(db: AsyncSession, user: Users, new_password_hash: str):
    """Update user password."""
    user.password = new_password_hash
    db.add(user)
    await db.flush()
    return user


# ==========================================================
# 🔹 SESSION CRUD
# ==========================================================

async def create_session_record(
    db: AsyncSession,
    user_id: int,
    access_token: str,
    refresh_token: str,
    login_time: datetime,
    access_token_expires_at: datetime,
    refresh_token_expires_at: datetime,
    device_info: Optional[str],
    ip: Optional[str],
) -> Sessions:
    """Insert a new session record for a user."""
    session_obj = Sessions(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        login_time=login_time,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
        device_info=device_info,
        ip=ip,
    )
    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj


async def get_session_by_access_token(db: AsyncSession, access_token: str) -> Optional[Sessions]:
    """Fetch a session using the access token."""
    result = await db.execute(select(Sessions).where(Sessions.access_token == access_token))
    return result.scalars().first()


async def get_session_by_user_id(db: AsyncSession, user_id: int) -> Optional[Sessions]:
    """Fetch the most recent session for a user."""
    result = await db.execute(
        select(Sessions)
        .where(Sessions.user_id == user_id)
        .order_by(Sessions.login_time.desc())
    )
    return result.scalars().first()


async def update_session_tokens(
    db: AsyncSession,
    session: Sessions,
    new_access_token: str,
    new_refresh_token: Optional[str],
    new_access_expiry: datetime,
    new_refresh_expiry: Optional[datetime],
):
    """Update access/refresh tokens and expiry times."""
    session.access_token = new_access_token
    session.refresh_token = new_refresh_token or session.refresh_token
    session.access_token_expires_at = new_access_expiry
    session.refresh_token_expires_at = new_refresh_expiry or session.refresh_token_expires_at
    db.add(session)
    await db.flush()
    return session


async def revoke_session_record(db: AsyncSession, session: Sessions, reason: Optional[str] = None):
    """Soft-delete or revoke a session (invalidate token)."""
    session.revoked_at = datetime.utcnow()
    session.revocation_reason = reason or "manual_revoke"
    db.add(session)
    await db.flush()
    return session


async def delete_expired_sessions(db: AsyncSession):
    """Delete expired sessions (cleanup)."""
    now = datetime.utcnow()
    stmt = delete(Sessions).where(Sessions.access_token_expires_at < now)
    await db.execute(stmt)
    await db.flush()
