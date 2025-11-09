from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD Imports
from app.crud.authentication.authentication import (
    get_user_by_email,
    get_user_by_id,
    get_session_by_access_token,
    revoke_session_record,
)

# Core Modules
from app.services.authentication_service import authentication_core
from app.core.exceptions import (
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ConflictError,
)

# Schemas & Models
from app.schemas.pydantic_models.users import UserCreate, TokenResponse
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.authentication import VerificationType

# Utilities for validation
from app.utils.auth_utils import is_valid_email, is_strong_password, is_valid_indian_phone


# ==========================================================
# 🔹 USER SIGNUP
# ==========================================================

async def signup(db: AsyncSession, payload: UserCreate, created_by: Optional[int] = None) -> Users:
    """
    User signup with email, password, and phone validation.
    
    Validations:
    - Email: standard email format
    - Password: strong password requirements (uppercase, lowercase, digit, special char)
    - Phone: Indian format (10 digits starting with 6-9)
    """
    
    if payload.role_id is not None and payload.role_id != 1:
        raise BadRequestError("Cannot create admin users via this endpoint")

    # ✅ Validate Email
    email_valid, email_error = is_valid_email(payload.email)
    if not email_valid:
        raise BadRequestError(f"Invalid email: {email_error}")

    # ✅ Validate Password
    password_valid, password_error = is_strong_password(payload.password)
    if not password_valid:
        raise BadRequestError(f"Weak password: {password_error}")

    # ✅ Validate Phone (if provided)
    if payload.phone_number:
        phone_valid, phone_error = is_valid_indian_phone(payload.phone_number)
        if not phone_valid:
            raise BadRequestError(f"Invalid phone number: {phone_error}")

    # ✅ Check if email already exists
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise ConflictError("Email already registered")

    user_record = await authentication_core.create_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=1,
        status_id=1,
        created_by=created_by,
    )
    return user_record


# ==========================================================
# 🔹 OTP GENERATION
# ==========================================================

async def request_otp(
    db: AsyncSession,
    email: str,
    verification_type: Optional[str],
    client_host: Optional[str] = None,
):
    user = await get_user_by_email(db, email)
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


# ==========================================================
# 🔹 OTP VERIFICATION & PASSWORD RESET
# ==========================================================

async def verify_otp_flow(
    db: AsyncSession,
    email: str,
    otp: str,
    verification_type: Optional[str] = None,
    new_password: Optional[str] = None,
):
    user = await get_user_by_email(db, email)
    if not user:
        raise NotFoundError("User not found")

    vtype_str = (verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise BadRequestError("Invalid verification_type")

    ok, verification_result = await authentication_core.verify_otp(db, user.user_id, otp, vtype)
    if not ok:
        raise BadRequestError(verification_result)

    if vtype == VerificationType.PASSWORD_RESET and new_password:
        await authentication_core.update_user_password(db, user, new_password)
        return {"message": "Password reset successful"}

    return {"message": "OTP verified"}


# ==========================================================
# 🔹 PASSWORD CHANGE
# ==========================================================

async def change_password(
    db: AsyncSession,
    current_user: Users,
    current_password: str,
    new_password: str,
):
    auth_user = await authentication_core.authenticate_user(
        db, email=current_user.email, password=current_password
    )
    if not auth_user:
        raise UnauthorizedError("Current password incorrect")

    await authentication_core.update_user_password(db, current_user, new_password)
    return {"message": "Password changed successfully"}


# ==========================================================
# 🔹 LOGIN
# ==========================================================

async def login_flow(
    db: AsyncSession,
    email: str,
    password: str,
    device_info: Optional[str] = None,
    client_host: Optional[str] = None,
) -> TokenResponse:
    user = await authentication_core.authenticate_user(db, email=email, password=password)
    if not user:
        raise UnauthorizedError("Invalid credentials")

    session = await authentication_core.create_session(
        db, user, device_info=device_info, ip=client_host
    )

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


# ==========================================================
# 🔹 TOKEN REFRESH
# ==========================================================

async def refresh_tokens(db: AsyncSession, access_token: str) -> TokenResponse:
    try:
        session = await authentication_core.refresh_access_token(db, access_token)
    except Exception as e:
        raise UnauthorizedError(str(e))

    user = await get_user_by_id(db, session.user_id)
    if not user:
        raise NotFoundError("User not found")

    expires_in = (
        int((session.access_token_expires_at - datetime.utcnow()).total_seconds())
        if session.access_token_expires_at
        else 3600
    )

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id,
    )


# ==========================================================
# 🔹 LOGOUT
# ==========================================================

async def logout_flow(db: AsyncSession, access_token: str):
    session = await get_session_by_access_token(db, access_token)
    if not session:
        raise NotFoundError("Session not found")

    await revoke_session_record(db, session=session, reason="user_logout")
    await db.commit()
    return {"message": "Logged out"}


# ==========================================================
# 🔹 ADMIN REGISTRATION
# ==========================================================

async def register_admin(
    db: AsyncSession,
    payload: UserCreate,
    current_user_id: int,
    user_permissions: dict,
):
    """
    Admin registration with email, password, and phone validation.
    
    Validations:
    - Email: standard email format
    - Password: strong password requirements (uppercase, lowercase, digit, special char)
    - Phone: Indian format (10 digits starting with 6-9)
    """
    
    # ✅ Validate Email
    email_valid, email_error = is_valid_email(payload.email)
    if not email_valid:
        raise BadRequestError(f"Invalid email: {email_error}")

    # ✅ Validate Password
    password_valid, password_error = is_strong_password(payload.password)
    if not password_valid:
        raise BadRequestError(f"Weak password: {password_error}")

    # ✅ Validate Phone (if provided)
    if payload.phone_number:
        phone_valid, phone_error = is_valid_indian_phone(payload.phone_number)
        if not phone_valid:
            raise BadRequestError(f"Invalid phone number: {phone_error}")

    # ✅ Check if email already exists
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise ConflictError("Email already registered")

    user_record = await authentication_core.create_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=payload.role_id,
        status_id=1,
        created_by=current_user_id,
    )
    return user_record
