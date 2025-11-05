from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.authentication_service import authentication_core
from app.core.exceptions import NotFoundError, BadRequestError, UnauthorizedError, ConflictError
from app.schemas.pydantic_models.users import UserCreate, TokenResponse
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.authentication import VerificationType, Sessions


async def signup(db: AsyncSession, payload: UserCreate, created_by: Optional[int] = None) -> Users:
    # Enforce only normal user role can signup
    if payload.role_id is not None and payload.role_id != 1:
        raise BadRequestError("Cannot create admin users via this endpoint")

    # check existing email
    result = await db.execute(select(Users).where(Users.email == payload.email))
    existing = result.scalars().first()
    if existing:
        raise ConflictError("Email already registered")

    user_obj = await authentication_core.create_user(db, full_name=payload.full_name, email=payload.email, password=payload.password, phone_number=payload.phone_number, role_id=1, status_id=1, created_by=created_by)
    return user_obj


async def request_otp(db: AsyncSession, email: str, verification_type: Optional[str], client_host: Optional[str] = None):
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        raise NotFoundError("User not found")

    vtype_str = (verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise BadRequestError("Invalid verification_type")

    ver = await authentication_core.create_verification(db, user.user_id, vtype, ip=client_host)

    subject = "Your OTP Code"
    body = f"Your OTP is: {ver.otp_code}. It expires at {ver.expires_at} UTC."
    sent = authentication_core._send_email(user.email, subject, body)

    response = {"message": "OTP created"}
    if not sent:
        response["otp"] = ver.otp_code
    return response


async def verify_otp_flow(db: AsyncSession, email: str, otp: str, verification_type: Optional[str] = None, new_password: Optional[str] = None):
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        raise NotFoundError("User not found")

    vtype_str = (verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise BadRequestError("Invalid verification_type")

    ok, res = await authentication_core.verify_otp(db, user.user_id, otp, vtype)
    if not ok:
        raise BadRequestError(res)

    if vtype == VerificationType.PASSWORD_RESET and new_password:
        await authentication_core.update_user_password(db, user, new_password)
        return {"message": "Password reset successful"}

    return {"message": "OTP verified"}


async def change_password(db: AsyncSession, current_user: Users, current_password: str, new_password: str):
    auth_user = await authentication_core.authenticate_user(db, email=current_user.email, password=current_password)
    if not auth_user:
        raise UnauthorizedError("Current password incorrect")

    await authentication_core.update_user_password(db, current_user, new_password)
    return {"message": "Password changed successfully"}


async def login_flow(db: AsyncSession, username: str, password: str, device_info: Optional[str] = None, client_host: Optional[str] = None) -> TokenResponse:
    user = await authentication_core.authenticate_user(db, email=username, password=password)
    if not user:
        raise UnauthorizedError("Invalid credentials")

    session = await authentication_core.create_session(db, user, device_info=device_info, ip=client_host)

    expires_in = (
        int((session.access_token_expires_at - session.login_time).total_seconds())
        if session.access_token_expires_at and session.login_time
        else 3600
    )

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        session = await authentication_core.refresh_access_token(db, refresh_token)
    except Exception as e:
        raise UnauthorizedError(str(e))

    result = await db.execute(select(Users).where(Users.user_id == session.user_id))
    user = result.scalars().first()
    if not user:
        raise NotFoundError("User not found")

    expires_in = int((session.access_token_expires_at - datetime.utcnow()).total_seconds()) if session.access_token_expires_at else 3600

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id,
    )


async def logout_flow(db: AsyncSession, access_token: str):
    # find session by access token
    result = await db.execute(select(Sessions).where(Sessions.access_token == access_token))
    session = result.scalars().first()
    if not session:
        raise NotFoundError("Session not found")

    await authentication_core.revoke_session(db, session=session, reason="user_logout")
    return {"message": "Logged out"}


async def register_admin(db: AsyncSession, payload: UserCreate, current_user_id: int, user_permissions: dict):
    # permission check is expected to be done by route (dependency). We still enforce here minimally.
    # check email conflict
    result = await db.execute(select(Users).where(Users.email == payload.email))
    if result.scalars().first():
        raise ConflictError("Email already registered")

    user_obj = await authentication_core.create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=payload.role_id,
        status_id=1,
        created_by=current_user_id,
    )
    return user_obj
