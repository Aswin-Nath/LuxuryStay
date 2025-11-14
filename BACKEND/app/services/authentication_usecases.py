from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# CRUD Imports
from app.crud.authentication import (
    get_user_by_email,
    get_user_by_id,
    get_session_by_access_token,
    get_session_by_user_id,
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
    revoke_session,
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
from app.models.sqlalchemy_schemas.authentication import VerificationType, BlacklistedTokens

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
        message="Login successful. Use the access_token in Authorization header as Bearer token.",
    )


# ==========================================================
# 🔹 TOKEN REFRESH
# ==========================================================

async def refresh_tokens(db: AsyncSession, current_user, access_token: str) -> TokenResponse:
    """
    Refresh access token using OAuth2 scheme extracted tokens.
    
    Security checks:
    1. Validates that the refresh token hasn't been blacklisted/revoked
    2. Checks if the session is still active
    3. If all checks pass, generates new access token (keeps same refresh_token for 7 days)
    
    The refresh token remains the same for 7 days, allowing multiple access token refreshes
    without needing to regenerate the refresh token. If user logs out or refresh token expires,
    they must login again.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        current_user (Users): The authenticated user from OAuth2 scheme.
        access_token (str): The current access token extracted from OAuth2 Bearer scheme.
    
    Returns:
        TokenResponse: Object with new access_token (same refresh_token), expires_in, token_type, role_id, and message.
    
    Raises:
        UnauthorizedException: If refresh token is blacklisted, session invalid, or token expired.
        NotFoundException: If user or session not found.
    """
    try:
        # Step 1: Get the most recent session for this user
        session = await get_session_by_user_id(db, current_user.user_id)
        if not session:
            raise UnauthorizedException("Session not found")
        
        # Step 2: Check if session is active (not already revoked)
        if not session.is_active:
            raise UnauthorizedException("Session has been revoked")
        
        # Step 3: Check if refresh token has been blacklisted (revoked during logout/security event)
        # This checks the session_id which covers both access and refresh tokens
        result = await db.execute(
            select(BlacklistedTokens).where(
                BlacklistedTokens.session_id == session.session_id
            )
        )
        blacklisted_token = result.scalars().first()
        
        if blacklisted_token:
            raise UnauthorizedException("Refresh token has been revoked (blacklisted). Please login again.")
        
        # Step 4: Refresh the access token (keeps same refresh_token & jti for 7 days)
        session = await refresh_access_token(db, session.access_token)
    except UnauthorizedException:
        raise
    except Exception as e:
        raise UnauthorizedException(str(e))

    # Step 5: Fetch user details for response
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
        refresh_token=session.refresh_token,  # ← Same refresh_token (valid for 7 days)
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id,
        message="Access token refreshed successfully. Use the new access_token in Authorization header for subsequent requests.",
    )


# ==========================================================
# 🔹 LOGOUT
# ==========================================================

async def logout_flow(db: AsyncSession, user_id: int):
    """
    User logout flow.
    
    Logs out the user by:
    1. Finding the most recent session for the user
    2. Verifying the session's JTI is NOT already blacklisted
    3. Checking if the session is still active
    4. Blacklisting both the access token and refresh token
    5. Marking the session as inactive
    
    This prevents token reuse and ensures the session is fully revoked.
    Uses user_id instead of access_token for reliable lookup even after token changes.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        user_id (int): The user ID of the user logging out.
    
    Returns:
        dict: Confirmation message.
    
    Raises:
        NotFoundException: If session not found.
        UnauthorizedException: If session is already revoked or JTI is blacklisted.
    """
    try:
        # Get the most recent session for this user
        session = await get_session_by_user_id(db, user_id)
        if not session:
            raise NotFoundException("Session not found")
        
        # Check if session is already revoked
        if not session.is_active:
            raise UnauthorizedException("Session already revoked")
        
        # Check if session's JTI is already in blacklist
        result = await db.execute(
            select(BlacklistedTokens).where(
                BlacklistedTokens.session_id == session.session_id
            )
        )
        blacklisted_token = result.scalars().first()
        
        if blacklisted_token:
            raise UnauthorizedException("Session has already been blacklisted")
        
        # Revoke the session (this blacklists both access and refresh tokens)
        await revoke_session(db, session=session, reason="user_logout")
        await db.commit()
        
    except (NotFoundException, UnauthorizedException):
        raise
    except Exception as e:
        raise UnauthorizedException(f"Logout failed: {str(e)}")
    
    return {"message": "Logged out successfully"}


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
