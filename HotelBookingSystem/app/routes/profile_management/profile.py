from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional

# DB & Auth
from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users

# Schemas
from app.schemas.pydantic_models.users import ProfileResponse, ProfileUpdate, ChangePasswordPayload

# Services
from app.services.profile_management.profile import (
    get_my_profile_service,
    update_my_profile_service,
    upload_profile_image_service,
    change_my_password_service,
)

router = APIRouter(prefix="/profile", tags=["PROFILE"])


# ==========================================================
# 🔹 READ - Get authenticated user's profile
# ==========================================================
# 🔹 GET PROFILE
# ==========================================================

@router.get("/", response_model=ProfileResponse)
async def get_my_profile(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Any:
    return await get_my_profile_service(db, current_user)


# ==========================================================
# 🔹 UPDATE - Modify user profile details
# ==========================================================
# 🔹 UPDATE PROFILE
# ==========================================================

@router.put("/", response_model=ProfileResponse)
async def update_my_profile(
    request: Request,
    payload: Optional[ProfileUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Update allowed profile fields."""
    content_type = request.headers.get("content-type", "")
    profile_update_data = {}
    if content_type.startswith("application/json"):
        profile_update_data = await request.json()
    elif payload:
        profile_update_data = payload.model_dump(exclude_unset=True)
    return await update_my_profile_service(db, current_user, profile_update_data)


# ==========================================================
# 🔹 UPDATE - Upload user profile image
# ==========================================================
# 🔹 UPLOAD PROFILE IMAGE
# ==========================================================

@router.post("/image", response_model=ProfileResponse)
async def upload_profile_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return await upload_profile_image_service(db, current_user, file)


# ==========================================================
# 🔹 UPDATE - Change user password
# ==========================================================
# 🔹 CHANGE PASSWORD
# ==========================================================

@router.put("/password")
async def change_my_password(
    payload: ChangePasswordPayload,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return await change_my_password_service(db, current_user, payload.current_password, payload.new_password)
