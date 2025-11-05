from fastapi import APIRouter, Depends, status, UploadFile, File, Request
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.schemas.pydantic_models.users import ProfileResponse, ProfileUpdate, ChangePasswordPayload
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.authentication_service.authentication_usecases import change_password as svc_change_password
from app.core.cache import invalidate_pattern, get_cached, set_cached

router = APIRouter(prefix="/api/profile", tags=["PROFILE"])

@router.get("/", response_model=ProfileResponse)
async def get_my_profile(current_user: Users = Depends(get_current_user)) -> Any:
	"""Return the authenticated user's profile."""
	cache_key = f"profile:user:{current_user.user_id}"
	cached = await get_cached(cache_key)
	if cached is not None:
		return cached

	result = ProfileResponse.model_validate(current_user)
	await set_cached(cache_key, result, ttl=300)
	return result

@router.put("/", response_model=ProfileResponse)
async def update_my_profile(
	request: Request,
	payload: Optional[ProfileUpdate],
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Update allowed profile fields. Accepts either JSON (application/json) or multipart/form-data (form fields).

	This endpoint handles only scalar/profile fields. Image uploads must use the dedicated
	POST /api/profile/image endpoint.
	"""
	# Determine content type and build the update dict.
	content_type = request.headers.get("content-type", "")

	# If JSON body was sent, use it directly.
	if content_type.startswith("application/json"):
		body = await request.json()
		data = body or {}
	else:
		# For multipart/form-data, we get form-parsed fields via the dependency.
		data = payload.model_dump(exclude_unset=True) if payload else {}

	if not data:
		return ProfileResponse.model_validate(current_user)

	# apply changes to the ORM user object and persist
	for k, v in data.items():
		if hasattr(current_user, k):
			setattr(current_user, k, v)

	db.add(current_user)
	await db.commit()
	await db.refresh(current_user)
	# invalidate profile cache for this user
	await invalidate_pattern(f"profile:user:{current_user.user_id}")
	return ProfileResponse.model_validate(current_user)


@router.post("/image", response_model=ProfileResponse)
async def upload_profile_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
	"""Upload a profile image and set the user's profile_image_url."""
	url = await save_uploaded_image(file)
	current_user.profile_image_url = url
	db.add(current_user)
	await db.commit()
	await db.refresh(current_user)
	# invalidate profile cache for this user
	await invalidate_pattern(f"profile:user:{current_user.user_id}")
	return ProfileResponse.model_validate(current_user)

@router.put("/password")
async def change_my_password(payload: ChangePasswordPayload, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
	"""Change current user's password by verifying current password."""
	await svc_change_password(db, current_user, payload.current_password, payload.new_password)
	return {"message": "Password changed successfully"}
