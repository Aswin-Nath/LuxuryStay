import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Request, Security, Response, Cookie, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.schemas.pydantic_models.users import UserCreate, UserResponse, TokenResponse

from app.services.authentication_usecases import (
    signup as svc_signup,
    request_otp as svc_request_otp,
    verify_otp_flow as svc_verify_otp,
    login_flow as svc_login_flow,
    refresh_tokens as svc_refresh_tokens,
    logout_flow as svc_logout_flow,
    register_admin as svc_register_admin,
)
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies.authentication import get_current_user, check_permission
auth_router = APIRouter(prefix="/auth", tags=["AUTH"])
SECURE_REFRESH_COOKIE = os.getenv("SECURE_REFRESH_COOKIE", "true").lower() in ("1", "true", "yes")
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth/refresh"
from pydantic import BaseModel
from typing import Optional
from app.core.security import oauth2_scheme


class OTPRequest(BaseModel):
    email: str
    verification_type: str


class OTPVerify(BaseModel):
    email: str
    otp: str
    verification_type: Optional[str] = "PASSWORD_RESET"
    new_password: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _set_refresh_cookie(response: Response, token: str, expires_at: Optional[datetime]):
    """Store the refresh token securely via HttpOnly cookie."""
    max_age = None
    expires_value = None
    if expires_at:
        expires_utc = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=timezone.utc)
        expires_utc = expires_utc.astimezone(timezone.utc)
        time_left = int((expires_utc - datetime.now(tz=timezone.utc)).total_seconds())
        if time_left > 0:
            max_age = time_left
        expires_value = expires_utc

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SECURE_REFRESH_COOKIE,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
        expires=expires_value,
    )



# ============================================================================
# 🔹 CREATE - Register new user account (Token-Based Signup)
# ============================================================================
@auth_router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: UserCreate,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and automatically issue access + refresh tokens.
    
    Behavior mirrors the login flow:
    - Creates new user.
    - Generates access + refresh tokens.
    - Sends refresh token via HttpOnly cookie.
    - Returns access token payload in body.
    """

    # 1️⃣ Create user
    user_obj = await svc_signup(db, payload)

    # 2️⃣ Generate tokens (reuse same service used by login)
    auth_result = await svc_login_flow(
        db=db,
        identifier=user_obj.email,         # or username
        password=payload.password,         # raw password user sent
        device_info=request.headers.get("user-agent"),
        client_host=request.client.host if request.client else None,
    )

    # 3️⃣ Set refresh token cookie
    _set_refresh_cookie(
        response,
        auth_result.refresh_token,
        auth_result.refresh_token_expires_at
    )

    # 4️⃣ Return the same TokenResponse used by login
    return auth_result.token_response


# ==================================================
# 🔹 CREATE - Request OTP for password reset or verification
# ==================================================
@auth_router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(payload: OTPRequest, request: Request = None, db: AsyncSession = Depends(get_db)):
    """
    Request an OTP for password reset or email verification.
    
    Generates a one-time password (OTP) sent to the user's email for verification or password
    reset flows. In development mode (no SMTP configured), the OTP is returned in the response
    for convenience. Each OTP expires after a configured duration (typically 15-30 minutes).
    
    Args:
        payload (OTPRequest): Request containing email and verification_type (PASSWORD_RESET or EMAIL_VERIFY).
        request (Request): HTTP request object for client host tracking.
        db (AsyncSession): Database session dependency.
    
    Returns:
        dict: Confirmation with message and (if dev mode) OTP code.
    
    Raises:
        HTTPException (404): If user with provided email not found.
        HTTPException (429): If OTP requested too frequently from same IP.
    """
    return await svc_request_otp(db, payload.email, payload.verification_type, client_host=request.client.host if request.client else None)


# ============================================================================
# 🔹 UPDATE - Verify OTP and optionally reset password
# ============================================================================
@auth_router.post("/otp/verify")
async def verify_otp_endpoint(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify OTP and optionally reset password.
    
    Validates a one-time password against the one sent to the user's email. For PASSWORD_RESET
    verification_type, if new_password is provided, updates the user's password. For EMAIL_VERIFY,
    confirms the user's email address. Invalidates the OTP after successful verification.
    
    Args:
        payload (OTPVerify): Request containing email, otp, verification_type, and optional new_password.
        db (AsyncSession): Database session dependency.
    
    Returns:
        dict: Confirmation with message and success status.
    
    Raises:
        HTTPException (400): If OTP is invalid or expired.
        HTTPException (404): If user not found.
    
    Side Effects:
        - Invalidates the OTP after verification.
        - Updates user password if verification_type is PASSWORD_RESET and new_password provided.
    """
    return await svc_verify_otp(db, payload.email, payload.otp, payload.verification_type, payload.new_password)





@auth_router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    User login endpoint (OAuth2 Password Flow).
    
    Authenticates user credentials (username/email and password) and issues JWT access and
    refresh tokens on successful authentication. Logs device information and client IP for
    security auditing. Implements rate limiting to prevent brute force attacks.
    
    Args:
        form_data (OAuth2PasswordRequestForm): OAuth2 form containing username (email) and password.
        request (Request): HTTP request object for device tracking and IP logging.
        db (AsyncSession): Database session dependency.
    
    Returns:
        TokenResponse: Contains access_token metadata (token_type, expires_in, role_id) while the refresh token is delivered via HttpOnly cookie.
    
    Raises:
        HTTPException (401): If credentials are invalid.
        HTTPException (429): If too many failed login attempts from same IP.
    
    Side Effects:
        - Creates audit log entry for login attempt.
        - Tracks device and IP for fraud detection.
    """
    auth_result = await svc_login_flow(
        db,
        form_data.username,
        form_data.password,
        device_info=request.headers.get("user-agent"),
        client_host=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, auth_result.refresh_token, auth_result.refresh_token_expires_at)
    return auth_result.token_response



@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Refresh JWT tokens using the HttpOnly refresh cookie.
    
    Reads the refresh token from the secure cookie. Validates it, rotates the
    access token, and refreshes the cookie with the same refresh token value.
    
    Args:
        response (Response): FastAPI response to set the refresh token cookie.
        db (AsyncSession): Database session dependency.
        refresh_token (str | None): Refresh token from HttpOnly cookie.
    
    Returns:
        TokenResponse: Updated access_token metadata (token_type, expires_in, role_id).
    
    Raises:
        HTTPException (401): If refresh token is missing, invalid, or revoked.
    """
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    auth_result = await svc_refresh_tokens(db, refresh_token)
    _set_refresh_cookie(response, auth_result.refresh_token, auth_result.refresh_token_expires_at)
    return auth_result.token_response



@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    User logout endpoint.
    
    Logs out the current user by blacklisting the access token and revoking the associated
    session. Prevents token reuse and forces re-authentication on the next request. Client
    should discard tokens after successful logout.
    
    Args:
        token (str): OAuth2 bearer token dependency extracted from Authorization header.
        db (AsyncSession): Database session dependency.
        current_user (Users): Currently authenticated user from OAuth2 scheme.
    
    Returns:
        dict: Confirmation message for successful logout.
    
    Raises:
        HTTPException (401): If token is invalid or already blacklisted.
    
    Side Effects:
        - Adds token to blacklist cache.
        - Invalidates user session.
        - Creates audit log entry.
    """
    return await svc_logout_flow(db, current_user.user_id)


# ==============================================================
# ADMIN CREATION (Permission-Protected)
# ==============================================================
@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Create a new Admin user (permission-protected).
    
    Administrative endpoint to register new admin users in the system. Only users with
    ADMIN_CREATION:WRITE permission can create admins. Created admins are assigned the ADMIN
    role and can immediately access admin features. Email must be unique and password must
    meet security requirements.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        payload (UserCreate): Admin user creation request with email, password, name, etc.
        db (AsyncSession): Database session dependency.
        current_user (Users): Currently authenticated user (verified non-basic user).
        token_payload (dict): Token payload (validated by Security dependency).
    
    Returns:
        UserResponse: Newly created admin user record with user_id and profile info.
    
    Raises:
        HTTPException (403): If user lacks ADMIN_CREATION:WRITE permission.
        HTTPException (409): If email already exists.
    
    Side Effects:
        - Assigns ADMIN role to new user.
        - Creates audit log entry for admin creation.
    """

    user_obj = await svc_register_admin(db, payload, current_user.user_id)
    return UserResponse.model_validate(user_obj)
