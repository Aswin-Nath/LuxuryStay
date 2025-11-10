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
@router.get("/", response_model=ProfileResponse)
async def get_my_profile(current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Any:
    """
    Retrieve authenticated user's profile information.
    
    Fetches current user's profile details including name, email, phone, address, role,
    profile image URL, and account timestamps. User data is specific to authenticated context.
    
    Args:
        current_user (Users): Authenticated user dependency.
        db (AsyncSession): Database session dependency.
    
    Returns:
        ProfileResponse: User profile with all details and profile image URL.
    
    Raises:
        HTTPException (404): If user record not found (should not happen if authenticated).
    """
    return await get_my_profile_service(db, current_user)


# ==========================================================
# 🔹 UPDATE - Modify user profile details
# ==========================================================
@router.put("/", response_model=ProfileResponse)
async def update_my_profile(
    request: Request,
    payload: Optional[ProfileUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Update authenticated user's profile information.
    
    Allows users to update their own profile fields (name, phone, address, bio, etc).
    Supports both JSON request bodies and form data. Immutable fields (email, role, created_at)
    are protected from modification. Changes are validated and persisted immediately.
    
    Args:
        request (Request): HTTP request (for content-type detection).
        payload (Optional[ProfileUpdate]): Profile update request body.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (owner of profile).
    
    Returns:
        ProfileResponse: Updated profile with modified fields.
    
    Raises:
        HTTPException (400): If attempting to modify protected fields.
        HTTPException (404): If user record not found.
    
    Side Effects:
        - Updates user record in database.
        - Updates updated_at timestamp.
    """
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
@router.post("/image", response_model=ProfileResponse)
async def upload_profile_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Upload or replace user's profile picture.
    
    Accepts image file upload and stores it via external provider. Replaces previous profile
    image if one exists (old image is deleted). Returns updated profile with new image URL.
    Supported formats: JPEG, PNG, WebP. Maximum file size enforced by upload service.
    
    Args:
        file (UploadFile): Image file to upload.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user updating profile image.
    
    Returns:
        ProfileResponse: Updated profile with new profile_image_url.
    
    Raises:
        HTTPException (400): If file format invalid or size exceeds limit.
        HTTPException (404): If user record not found.
    
    Side Effects:
        - Uploads file to external storage provider.
        - Deletes old profile image from storage.
        - Updates user's profile_image_url field.
    """


# ==========================================================
# 🔹 UPDATE - Change user password
# ==========================================================
@router.put("/password")
async def change_my_password(
    payload: ChangePasswordPayload,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Change authenticated user's password.
    
    Updates user's password after verifying current password matches. Enforces password
    strength requirements and prevents password reuse. After successful change, user's
    existing sessions remain valid (no forced re-authentication). Password is hashed
    using industry-standard algorithms before storage.
    
    Args:
        payload (ChangePasswordPayload): Request with current_password and new_password.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user changing password.
    
    Returns:
        dict: Confirmation message for successful password change.
    
    Raises:
        HTTPException (401): If current_password is incorrect.
        HTTPException (400): If new_password doesn't meet strength requirements or is same as current.
    
    Side Effects:
        - Updates user's password hash in database.
        - Creates audit log entry.
        - Invalidates any cached user session data.
    """
