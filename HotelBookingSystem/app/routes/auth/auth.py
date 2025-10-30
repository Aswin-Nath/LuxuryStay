from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.orm.users import Users
from app.models.orm.roles import Roles
from app.models.orm.authentication import Sessions, Verifications, VerificationType
from app.models.postgres.users import UserCreate, LoginRequest, UserResponse, TokenResponse
from app.services.auth import (
    create_user,
    authenticate_user,
    create_session,
    create_verification,
    verify_otp,
    update_user_password,
    _send_email,
)
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies.authentication import get_current_user,get_user_permissions
auth_router = APIRouter(prefix="/auth", tags=["AUTH"])
from app.models.orm.permissions import Resources, PermissionTypes
from pydantic import BaseModel
from typing import Optional
from app.core.security import oauth2_scheme
from app.services.auth import blacklist_token, revoke_session, refresh_access_token
from datetime import datetime


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


class RefreshRequest(BaseModel):
    refresh_token: str


@auth_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Enforce only normal user role can signup (not admin)
    # The system's 'user' role id is 1 per DB note; if client supplies different role, reject
    if payload.role_id is not None and payload.role_id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create admin users via this endpoint")

    # check existing email
    result = await db.execute(select(Users).where(Users.email == payload.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user_obj = await create_user(db, full_name=payload.full_name, email=payload.email, password=payload.password, phone_number=payload.phone_number, role_id=1,status_id=1)

    return UserResponse.model_validate(user_obj)


# ==================================================
# OTP / PASSWORD RESET / CHANGE PASSWORD endpoints
# ==================================================


@auth_router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(payload: OTPRequest, request: Request = None, db: AsyncSession = Depends(get_db)):
    """Request an OTP for password reset or signin verification.
    If SMTP is not configured the generated OTP will be returned in the response (dev convenience).
    """
    # find user
    result = await db.execute(select(Users).where(Users.email == payload.email))
    user = result.scalars().first()
    if not user:
        # Do not reveal user absence — but here we choose 404 to be explicit per existing patterns
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # map verification type
    vtype_str = (payload.verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification_type")

    ver = await create_verification(db, user.user_id, vtype, ip=request.client.host if request.client else None)

    # send email (best-effort)
    subject = "Your OTP Code"
    body = f"Your OTP is: {ver.otp_code}. It expires at {ver.expires_at} UTC."
    sent = _send_email(user.email, subject, body)

    # if SMTP not configured, return OTP for dev testing
    response = {"message": "OTP created"}
    if not sent:
        response["otp"] = ver.otp_code
    return response


@auth_router.post("/otp/verify")
async def verify_otp_endpoint(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify an OTP. If verification_type is PASSWORD_RESET and new_password is provided,
    update the user's password.
    """
    result = await db.execute(select(Users).where(Users.email == payload.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    vtype_str = (payload.verification_type or "PASSWORD_RESET").upper()
    try:
        vtype = VerificationType[vtype_str]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification_type")

    ok, res = await verify_otp(db, user.user_id, payload.otp, vtype)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res)

    # If password reset flow and new_password provided -> update
    if vtype == VerificationType.PASSWORD_RESET and payload.new_password:
        await update_user_password(db, user, payload.new_password)
        return {"message": "Password reset successful"}

    return {"message": "OTP verified"}


@auth_router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Authenticated endpoint to change password given current password."""
    # verify current password
    auth_user = await authenticate_user(db, email=current_user.email, password=payload.current_password)
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password incorrect")

    await update_user_password(db, current_user, payload.new_password)
    return {"message": "Password changed successfully"}


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 Login endpoint that returns JWT tokens on successful authentication.
    """
    # Authenticate user by email/username
    user = await authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create a session + tokens
    session = await create_session(
        db,
        user,
        device_info=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
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
        role_id=user.role_id
    )



@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh (rotate) access and refresh tokens using a valid refresh token."""
    try:
        session = await refresh_access_token(db, payload.refresh_token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # fetch user to return role_id
    result = await db.execute(select(Users).where(Users.user_id == session.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    expires_in = int((session.access_token_expires_at - datetime.utcnow()).total_seconds()) if session.access_token_expires_at else 3600

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id,
    )



@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Logout: blacklist tokens and revoke the session associated with the provided access token."""
    # find session by access token
    result = await db.execute(select(Sessions).where(Sessions.access_token == token))
    session = result.scalars().first()
    if not session:
        # If session not found, still respond with 200 to avoid token probing; but here we choose 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await revoke_session(db, session=session, reason="user_logout")
    return {"message": "Logged out"}


# ==============================================================
# 🧠 ADMIN CREATION (Permission-Protected)
# ==============================================================
@auth_router.post("/admin/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Endpoint to create Admin users.
    Requires `Admin_Creation` resource with `WRITE` permission.
    """

    # ----------------------------------------------------------
    # 🔐 Permission Check
    # ----------------------------------------------------------
    print("THIS",user_permissions)
    allowed = (
        Resources.Admin_Creation in user_permissions
        and PermissionTypes.WRITE in user_permissions[Resources.Admin_Creation]
        )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create Admins",
        )

    # ----------------------------------------------------------
    # 🧭 Email Conflict Check
    # ----------------------------------------------------------
    existing_email_query = await db.execute(select(Users).where(Users.email == payload.email))
    if existing_email_query.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # ----------------------------------------------------------
    # 🧱 Create Admin
    # ----------------------------------------------------------
    user_obj = await create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=payload.role_id,  # Admin Role ID
        status_id=1,
        created_by=current_user.user_id
    )

    return UserResponse.model_validate(user_obj)
