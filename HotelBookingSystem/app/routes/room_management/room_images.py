from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    status,
    Query,
)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.room_service.images_service import create_image, get_images_for_room
from app.services.room_service.images_service import hard_delete_image, set_image_primary
from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.images import ImageResponse
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/rooms/{room_id}/images", tags=["ROOM_IMAGES"])


# ==============================================================
# 🔹 CREATE - Upload a new image for room
# ==============================================================
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ImageResponse)
async def upload_image_for_room(
    room_type_id: int,
    image: UploadFile = File(...),  # ✅ Corrected here (was Form)
    caption: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    # ----------------------------------------------------------
    # Permission check: require room_service.WRITE
    # ----------------------------------------------------------
    allowed = (
        Resources.ROOM_MANAGEMENT.value in (user_permissions or {})
        and PermissionTypes.WRITE.value in (user_permissions or {})[Resources.ROOM_MANAGEMENT.value]
    )
    if not allowed:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Insufficient permissions to upload room images")
    """
    Upload a new image for a room.
    Accepts multipart/form-data with image, caption, and is_primary flag.
    """
    try:
        image_url = await save_uploaded_image(image)
        
        image_record = await create_image(
            db,
            entity_type="room_type",
            entity_id=room_type_id,
            image_url=image_url,
            caption=caption,
            is_primary=is_primary,
            uploaded_by=current_user.user_id,
        )
        # audit image create
        try:
            new_val = ImageResponse.model_validate(image_record).model_dump()
            entity_id = f"room_type:{room_type_id}:image:{getattr(image_record, 'image_id', None)}"
            await log_audit(entity="room_image", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
        except Exception:
            pass
        return ImageResponse.model_validate(image_record)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==============================================================
# 🔹 READ - Get all images for a room
# ==============================================================
@router.get("/", response_model=List[ImageResponse])
async def list_images_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all images associated with a specific room.
    """
    items = await get_images_for_room(db, room_id)
    return [ImageResponse.model_validate(i) for i in items]


# ==============================================================
# 🔹 DELETE - Remove images from room
# ==============================================================
@router.delete("/", status_code=status.HTTP_200_OK)
async def delete_images_for_room(
    image_ids: List[int] = Query(..., description="List of image IDs to delete"),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Hard-delete one or more images. The requester must be the uploader of each image or have room_service.WRITE."""
    # Call hard_delete_image for each id to reuse permission checks per-image
    for image_id in image_ids:
        await hard_delete_image(db, image_id, requester_id=current_user.user_id, requester_permissions=user_permissions)
    return {"message":"images deleted"}


# ==============================================================
# 🔹 UPDATE - Mark image as primary for room
# ==============================================================
@router.put("/{image_id}/primary", status_code=status.HTTP_200_OK)
async def mark_image_primary(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Mark a specific image as primary for the room's images. Only the uploader or users with ROOM_MANAGEMENT.WRITE may do this."""
    await set_image_primary(db, image_id, requester_id=current_user.user_id, requester_permissions=user_permissions)
    return {"message": "Image marked as primary"}
