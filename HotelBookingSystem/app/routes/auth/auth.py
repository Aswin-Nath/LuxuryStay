from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.roles import Roles
from app.models.sqlalchemy_schemas.authentication import Sessions, Verifications, VerificationType
from app.models.pydantic_models.users import UserCreate, LoginRequest, UserResponse, TokenResponse
from app.services.auth import (
    authenticate_user,
    create_session,
    create_verification,
    verify_otp,
    update_user_password,
    _send_email,
)
from app.services.auth_service import (
    signup as svc_signup,
    request_otp as svc_request_otp,
    verify_otp_flow as svc_verify_otp,
    change_password as svc_change_password,
    login_flow as svc_login_flow,
    refresh_tokens as svc_refresh_tokens,
    logout_flow as svc_logout_flow,
    register_admin as svc_register_admin,
)
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies.authentication import get_current_user,get_user_permissions
auth_router = APIRouter(prefix="/auth", tags=["AUTH"])
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
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
    user_obj = await svc_signup(db, payload)
    return UserResponse.model_validate(user_obj)


# ==================================================
# OTP / PASSWORD RESET / CHANGE PASSWORD endpoints
# ==================================================


@auth_router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(payload: OTPRequest, request: Request = None, db: AsyncSession = Depends(get_db)):
    """Request an OTP for password reset or signin verification.
    If SMTP is not configured the generated OTP will be returned in the response (dev convenience).
    """
    return await svc_request_otp(db, payload.email, payload.verification_type, client_host=request.client.host if request.client else None)


@auth_router.post("/otp/verify")
async def verify_otp_endpoint(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify an OTP. If verification_type is PASSWORD_RESET and new_password is provided,
    update the user's password.
    """
    return await svc_verify_otp(db, payload.email, payload.otp, payload.verification_type, payload.new_password)


@auth_router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Authenticated endpoint to change password given current password."""
    return await svc_change_password(db, current_user, payload.current_password, payload.new_password)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 Login endpoint that returns JWT tokens on successful authentication.
    """
    token_resp = await svc_login_flow(db, form_data.username, form_data.password, device_info=request.headers.get("user-agent"), client_host=request.client.host if request.client else None)
    return token_resp



@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh (rotate) access and refresh tokens using a valid refresh token."""
    return await svc_refresh_tokens(db, payload.refresh_token)



@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Logout: blacklist tokens and revoke the session associated with the provided access token."""
    return await svc_logout_flow(db, token)


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
    # Permission check (route dependency already enforces, but double-check)
    allowed = (
        Resources.ADMIN_CREATION.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ADMIN_CREATION.value]
    )
    if not allowed:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Insufficient permissions to create Admins")

    user_obj = await svc_register_admin(db, payload, current_user.user_id, user_permissions)
    return UserResponse.model_validate(user_obj)
