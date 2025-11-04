from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    status,
)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.room_service.images_service import create_image, get_images_for_room
from app.services.room_service.images_service import hard_delete_image
from app.database.postgres_connection import get_db
from app.models.pydantic_models.images import ImageResponse
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes


router = APIRouter(prefix="/api/rooms/{room_id}/images", tags=["ROOM_IMAGES"])


# ==============================================================
# POST: Upload Image For Room
# ==============================================================
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ImageResponse)
async def upload_image_for_room(
    room_id: int,
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
        Resources.room_service.value in (user_permissions or {})
        and PermissionTypes.WRITE.value in (user_permissions or {})[Resources.room_service.value]
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

        obj = await create_image(
            db,
            entity_type="room",
            entity_id=room_id,
            image_url=image_url,
            caption=caption,
            is_primary=is_primary,
            uploaded_by=current_user.user_id,
        )
        return ImageResponse.model_validate(obj)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==============================================================
# GET: List Images For Room
# ==============================================================
@router.get("/", response_model=List[ImageResponse])
async def list_images_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all images associated with a specific room.
    """
    items = await get_images_for_room(db, room_id)
    return [ImageResponse.model_validate(i) for i in items]


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_for_room(room_id: int, image_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), user_permissions: dict = Depends(get_user_permissions)):
    """Hard-delete an image (remove DB row). The requester must be the uploader or have room_service.WRITE."""
    await hard_delete_image(db, image_id, requester_id=current_user.user_id, requester_permissions=user_permissions)
    return None
