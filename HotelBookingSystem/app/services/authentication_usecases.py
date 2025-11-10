from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD Imports
from app.crud.authentication import (
    get_user_by_email,
    get_user_by_id,
    get_session_by_access_token,
    revoke_session_record,
)

# Core Modules & Services
from app.utils.authentication_util import (
    create_user,
    create_verification,
    verify_otp,
    update_user_password,
    authenticate_user,
    create_session,
    refresh_access_token,
    _send_email,
)
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    UnauthorizedException,
    ConflictException,
)

# Schemas & Models
from app.schemas.pydantic_models.users import UserCreate, TokenResponse
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.authentication import VerificationType

# Utilities for validation
from app.utils.authentication_util import is_valid_email, is_strong_password, is_valid_indian_phone


# ==========================================================
# 🔹 USER SIGNUP
# ==========================================================

async def signup(db: AsyncSession, payload: UserCreate, created_by: Optional[int] = None) -> Users:
    """
    User signup with comprehensive validation.
    
    Creates a new user account with email, password, and phone validation.
    Only basic users (role_id=1) can be created through this endpoint.
    
    Validations performed:
    - Email: Standard email format validation
    - Password: Strong password requirements (uppercase, lowercase, digit, special char, min 8 chars)
    - Phone: Indian phone format (10 digits starting with 6-9)
    - Email uniqueness: No duplicate emails allowed
    
    Args:
        db (AsyncSession): Database session for executing queries.
        payload (UserCreate): Pydantic model with full_name, email, password, phone_number.
        created_by (Optional[int]): User ID of admin creating this user (if applicable).
    
    Returns:
        Users: The newly created user record with user_id assigned.
    
    Raises:
        BadRequestException: If email format invalid, password weak, phone invalid, or admin creation attempted.
        ConflictException: If email already registered.
    """
    
    # ✅ Validate Email
    email_valid, email_error = is_valid_email(payload.email)
    if not email_valid:
        raise BadRequestException(f"Invalid email: {email_error}")

    # ✅ Validate Password
    password_valid, password_error = is_strong_password(payload.password)
    if not password_valid:
        raise BadRequestException(f"Weak password: {password_error}")

    # ✅ Validate Phone (if provided)
    if payload.phone_number:
        phone_valid, phone_error = is_valid_indian_phone(payload.phone_number)
        if not phone_valid:
            raise BadRequestException(f"Invalid phone number: {phone_error}")

    # ✅ Check if email already exists
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise ConflictException("Email already registered")

    user_record = await create_user(
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
    """
    Generate and send OTP for email verification or password reset.
    
    Creates an OTP verification record and sends it via email (if configured).
    If email sending fails, OTP is returned in response for testing purposes.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        email (str): User's email address.
        verification_type (Optional[str]): Type of verification (PASSWORD_RESET, EMAIL_VERIFICATION, etc).
        client_host (Optional[str]): Client IP address for logging purposes.
    
    Returns:
        dict: Message indicating OTP created; may include otp_code if email send failed.
    
    Raises:
        NotFoundException: If user with given email not found.
        BadRequestException: If verification_type is invalid.
    """
    user = await get_user_by_email(db, email)
    if not user:
        raise NotFoundException("User not found")

    vtype_str = (verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise BadRequestException("Invalid verification_type")

    ver = await create_verification(db, user.user_id, vtype, ip=client_host)
    subject = "Your OTP Code"
    body = f"Your OTP is: {ver.otp_code}. It expires at {ver.expires_at} UTC."
    sent = _send_email(user.email, subject, body)

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
    """
    Verify OTP and optionally reset password.
    
    Validates OTP against stored verification record. If verification type is PASSWORD_RESET
    and new_password is provided, updates user's password.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        email (str): User's email address.
        otp (str): The OTP code to verify.
        verification_type (Optional[str]): Type of verification (PASSWORD_RESET, EMAIL_VERIFICATION, etc).
        new_password (Optional[str]): New password (required for PASSWORD_RESET type).
    
    Returns:
        dict: Success message with "message" key.
    
    Raises:
        NotFoundException: If user with email not found.
        BadRequestException: If OTP invalid, expired, or verification_type invalid.
        UnauthorizedException: If OTP verification fails.
    """
    user = await get_user_by_email(db, email)
    if not user:
        raise NotFoundException("User not found")

    vtype_str = (verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise BadRequestException("Invalid verification_type")

    ok, verification_result = await verify_otp(db, user.user_id, otp, vtype)
    if not ok:
        raise BadRequestException(verification_result)

    if vtype == VerificationType.PASSWORD_RESET and new_password:
        await update_user_password(db, user, new_password)
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
    """
    Change password for authenticated user.
    
    Validates current password before allowing change to new password.
    New password must meet strong password requirements.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        current_user (Users): The authenticated user object.
        current_password (str): User's current password for verification.
        new_password (str): The new password to set.
    
    Returns:
        dict: Success message with "message" key.
    
    Raises:
        UnauthorizedException: If current password is incorrect.
        BadRequestException: If new password doesn't meet requirements.
    """
    auth_user = await authenticate_user(
        db, email=current_user.email, password=current_password
    )
    if not auth_user:
        raise UnauthorizedException("Current password incorrect")

    await update_user_password(db, current_user, new_password)
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
    """
    Authenticate user and create login session.
    
    Validates email and password credentials, creates a session record,
    and returns access and refresh tokens.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        email (str): User's email address.
        password (str): User's password (plain text, validated against hash).
        device_info (Optional[str]): Device information for session tracking.
        client_host (Optional[str]): Client IP address for session logging.
    
    Returns:
        TokenResponse: Object with access_token, refresh_token, expires_in, token_type, role_id.
    
    Raises:
        UnauthorizedException: If email/password combination is invalid.
    """
    user = await authenticate_user(db, email=email, password=password)
    if not user:
        raise UnauthorizedException("Invalid credentials")

    session = await create_session(
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
    """
    Refresh access token using current access token.
    
    Validates existing access token and generates a new one with extended expiration.
    Useful for extending user sessions without re-authentication.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        access_token (str): The current/existing access token.
    
    Returns:
        TokenResponse: Object with new access_token, refresh_token, expires_in, token_type, role_id.
    
    Raises:
        UnauthorizedException: If access_token is invalid or expired.
        NotFoundException: If user associated with token not found.
    """
    try:
        session = await refresh_access_token(db, access_token)
    except Exception as e:
        raise UnauthorizedException(str(e))

    user = await get_user_by_id(db, session.user_id)
    if not user:
        raise NotFoundException("User not found")

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
        raise NotFoundException("Session not found")

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
        raise BadRequestException(f"Invalid email: {email_error}")

    # ✅ Validate Password
    password_valid, password_error = is_strong_password(payload.password)
    if not password_valid:
        raise BadRequestException(f"Weak password: {password_error}")

    # ✅ Validate Phone (if provided)
    if payload.phone_number:
        phone_valid, phone_error = is_valid_indian_phone(payload.phone_number)
        if not phone_valid:
            raise BadRequestException(f"Invalid phone number: {phone_error}")

    # ✅ Check if email already exists
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise ConflictException("Email already registered")

    user_record = await create_user(
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
