from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

# CRUD imports
from app.crud.profile_management.profile import (
    get_user_by_id,
    update_user_profile,
    update_user_profile_image,
    update_user_password,
)

# External modules
from app.schemas.pydantic_models.users import ProfileResponse
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.authentication_service.authentication_usecases import change_password as svc_change_password
from app.core.cache import invalidate_pattern, get_cached, set_cached
from app.utils.audit_helper import log_audit


# ==========================================================
# 🔹 GET PROFILE
# ==========================================================

async def get_my_profile_service(db: AsyncSession, current_user):
    """Fetch authenticated user's profile (with cache)."""
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
    """Update user profile fields."""
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
    """Upload and save user profile image."""
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
    """Verify and update password."""
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
