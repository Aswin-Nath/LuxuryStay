from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

# CRUD imports
from app.crud.profile import (
    get_user_by_id,
    update_user_profile,
    update_user_profile_image,
    update_user_password,
)

# External modules
from app.schemas.pydantic_models.users import ProfileResponse
from app.services.image_upload_service import save_uploaded_image
from app.services.authentication_usecases import change_password as svc_change_password
from app.core.cache import invalidate_pattern, get_cached, set_cached
from app.utils.audit_util import log_audit


# ==========================================================
# 🔹 GET PROFILE
# ==========================================================

async def get_my_profile_service(db: AsyncSession, current_user):
    """
    Retrieve authenticated user's profile with caching.
    
    Fetches the current user's profile information including personal details, contact info,
    and preferences. Results are cached for 5 minutes to reduce database load. Cache is
    invalidated on any profile updates.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        current_user: The authenticated user object.
    
    Returns:
        ProfileResponse: User profile data validated against schema.
    
    Raises:
        HTTPException (404): If user record not found in database.
    """
    cache_key = f"profile:user:{current_user.user_id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    user_obj = await get_user_by_id(db, current_user.user_id)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    response = ProfileResponse.model_validate(user_obj)
    await set_cached(cache_key, response, ttl=300)
    return response


# ==========================================================
# 🔹 UPDATE PROFILE
# ==========================================================

async def update_my_profile_service(db: AsyncSession, current_user, data: dict):
    """
    Update user profile information.
    
    Updates user profile fields such as name, email, phone, address, etc. Validates data,
    persists changes, invalidates cache, and logs audit entry for compliance. Returns
    updated profile with all current information.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        current_user: The authenticated user whose profile is being updated.
        data (dict): Dictionary of profile fields to update (e.g., first_name, last_name, phone).
    
    Returns:
        ProfileResponse: Updated user profile after changes.
    
    Side Effects:
        - Invalidates profile cache
        - Creates audit log entry for update
    """
    if not data:
        return ProfileResponse.model_validate(current_user)

    updated_user = await update_user_profile(db, current_user, data)
    await db.commit()

    # Invalidate cache
    await invalidate_pattern(f"profile:user:{current_user.user_id}")

    # Log audit
    try:
        new_val = ProfileResponse.model_validate(updated_user).model_dump()
        entity_id = f"user:{current_user.user_id}"
        await log_audit(
            entity="user",
            entity_id=entity_id,
            action="UPDATE",
            new_value=new_val,
            changed_by_user_id=current_user.user_id,
            user_id=current_user.user_id,
        )
    except Exception:
        pass

    return ProfileResponse.model_validate(updated_user)


# ==========================================================
# 🔹 UPLOAD PROFILE IMAGE
# ==========================================================

async def upload_profile_image_service(db: AsyncSession, current_user, file):
    """
    Upload and save user profile image.
    
    Accepts an image file, saves it to cloud storage, updates the user's profile_image_url,
    persists the change, invalidates cache, and logs audit entry. Supports standard image
    formats (jpg, png, etc.).
    
    Args:
        db (AsyncSession): Database session for executing queries.
        current_user: The authenticated user uploading the profile image.
        file: UploadFile object from FastAPI (multipart form data).
    
    Returns:
        ProfileResponse: Updated user profile with new profile_image_url.
    
    Side Effects:
        - Uploads file to cloud storage (e.g., S3)
        - Invalidates profile cache
        - Creates audit log entry
    """
    url = await save_uploaded_image(file)
    updated_user = await update_user_profile_image(db, current_user, url)
    await db.commit()

    await invalidate_pattern(f"profile:user:{current_user.user_id}")

    try:
        new_val = ProfileResponse.model_validate(updated_user).model_dump()
        entity_id = f"user:{current_user.user_id}"
        await log_audit(
            entity="user",
            entity_id=entity_id,
            action="UPDATE",
            new_value=new_val,
            changed_by_user_id=current_user.user_id,
            user_id=current_user.user_id,
        )
    except Exception:
        pass

    return ProfileResponse.model_validate(updated_user)


# ==========================================================
# 🔹 CHANGE PASSWORD
# ==========================================================

async def change_my_password_service(db: AsyncSession, current_user, current_password: str, new_password: str):
    """
    Verify and update user password.
    
    Changes the authenticated user's password after verifying the current password is correct.
    Validates new password against strength requirements, updates database, invalidates cache,
    and logs audit entry. User remains authenticated after successful change.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        current_user: The authenticated user changing their password.
        current_password (str): User's current password (must match for verification).
        new_password (str): New password (must meet strength requirements).
    
    Returns:
        dict: Confirmation message {"message": "Password changed successfully"}.
    
    Raises:
        HTTPException (400): If current password is incorrect or new password doesn't meet requirements.
    
    Side Effects:
        - Invalidates profile cache
        - Creates audit log entry for security tracking
    """
    await svc_change_password(db, current_user, current_password, new_password)

    # Invalidate cache
    await invalidate_pattern(f"profile:user:{current_user.user_id}")

    try:
        entity_id = f"user:{current_user.user_id}"
        await log_audit(
            entity="user",
            entity_id=entity_id,
            action="UPDATE",
            new_value={"password_changed": True},
            changed_by_user_id=current_user.user_id,
            user_id=current_user.user_id,
        )
    except Exception:
        pass

    return {"message": "Password changed successfully"}
