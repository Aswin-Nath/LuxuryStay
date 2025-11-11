from fastapi import (
    APIRouter,
    Depends,
    Security,
    status,
    Query,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# ==========================================================
# 🧩 Core Modules
# ==========================================================
from app.database.postgres_connection import get_db
from app.dependencies.authentication import check_permission, get_current_user
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit

# ==========================================================
# 🧱 Schemas
# ==========================================================
from app.schemas.pydantic_models.room import (
    RoomTypeCreate,
    RoomTypeResponse,
    RoomTypeUpdate,
    RoomCreate,
    RoomResponse,
    Room,
    RoomUpdate,
    BulkRoomUploadResponse,
    AmenityCreate,
    AmenityResponse,
    Amenity,
    RoomAmenityMapCreate,
    RoomAmenityMapResponse,
)
from app.schemas.pydantic_models.images import ImageResponse
from app.models.sqlalchemy_schemas.users import Users

# ==========================================================
# ⚙️ Services
# ==========================================================
from app.services.rooms import (
    # Room Type Services
    create_room_type as svc_create_room_type,
    list_room_types as svc_list_room_types,
    get_room_type as svc_get_room_type,
    update_room_type as svc_update_room_type,
    soft_delete_room_type as svc_soft_delete_room_type,

    # Room Services
    create_room as svc_create_room,
    list_rooms as svc_list_rooms,
    get_room as svc_get_room,
    update_room as svc_update_room,
    delete_room as svc_delete_room,
    bulk_upload_rooms as svc_bulk_upload_rooms,

    # Amenity Services
    create_amenity as svc_create_amenity,
    list_amenities as svc_list_amenities,
    get_amenity as svc_get_amenity,
    delete_amenity as svc_delete_amenity,
    map_amenity as svc_map_amenity,
    get_rooms_for_amenity as svc_get_rooms_for_amenity,
    get_amenities_for_room as svc_get_amenities_for_room,
    unmap_amenity as svc_unmap_amenity,
    map_amenities_bulk as svc_map_amenities_bulk,
    unmap_amenities_bulk as svc_unmap_amenities_bulk,
)

# Image utilities
from app.services.image_upload_service import save_uploaded_image
from app.utils.images_util import (
    create_image,
    get_images_for_room,
    hard_delete_image,
    set_image_primary,
)

# ==========================================================
# 📦 Router Definition
# ==========================================================
router = APIRouter(prefix="/room-management", tags=["ROOM_MANAGEMENT"])


# ==========================================================
# 🏷️ ROOM TYPES
# ==========================================================
@router.post("/types", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(
    payload: RoomTypeCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    room_type_record = await svc_create_room_type(db, payload)
    try:
        new_val = RoomTypeResponse.model_validate(room_type_record).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_record.room_type_id}", action="INSERT", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(room_type_record).model_copy(update={"message": "Room type created"})


@router.get("/types", response_model=List[RoomTypeResponse])
async def get_room_types(
    room_type_id: Optional[int] = Query(None),
    include_deleted: Optional[bool] = Query(False),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if room_type_id is not None:
        room_type_record = await svc_get_room_type(db, room_type_id)
        return [RoomTypeResponse.model_validate(room_type_record)]

    cache_key = f"room_types:include_deleted:{include_deleted}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    items = await svc_list_room_types(db, include_deleted=include_deleted)
    response_list = [RoomTypeResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in items]
    await set_cached(cache_key, response_list, ttl=300)
    return response_list


@router.put("/types/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(
    room_type_id: int,
    payload: RoomTypeUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    room_type_record = await svc_update_room_type(db, room_type_id, payload)
    try:
        new_val = RoomTypeResponse.model_validate(room_type_record).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_id}", action="UPDATE", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(room_type_record).model_copy(update={"message": "Updated successfully"})


@router.delete("/types/{room_type_id}")
async def soft_delete_room_type(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"]),
):
    await svc_soft_delete_room_type(db, room_type_id)
    await invalidate_pattern("room_types:*")
    return {"message": "Room type soft-deleted"}


# ==========================================================
# 🖼️ ROOM TYPE IMAGES
# ==========================================================
@router.post("/types/{room_type_id}/images", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_room_type_image(
    room_type_id: int,
    image: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
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
        new_val = ImageResponse.model_validate(image_record).model_dump()
        await log_audit(entity="room_image", entity_id=f"room_type:{room_type_id}:image:{image_record.image_id}", action="INSERT", new_value=new_val)
        return ImageResponse.model_validate(image_record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/types/{room_type_id}/images", response_model=List[ImageResponse])
async def list_room_type_images(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: Users = Depends(get_current_user),
):
    items = await get_images_for_room(db, room_type_id)
    return [ImageResponse.model_validate(i) for i in items]


@router.put("/types/{room_type_id}/images/{image_id}/primary", status_code=status.HTTP_200_OK)
async def mark_room_type_image_primary(
    room_type_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    await set_image_primary(db, image_id, requester_id=current_user.user_id)
    return {"message": "Image marked as primary"}


@router.delete("/types/{room_type_id}/images", status_code=status.HTTP_200_OK)
async def delete_room_type_images(
    room_type_id: int,
    image_ids: List[int] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"]),
):
    for image_id in image_ids:
        await hard_delete_image(db, image_id, requester_id=current_user.user_id)
    return {"message": "Images deleted successfully"}


# ==========================================================
# 🏨 ROOMS SECTION
# ==========================================================
@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    room_record = await svc_create_room(db, payload)
    try:
        new_val = RoomResponse.model_validate(room_record).model_dump()
        await log_audit(entity="room", entity_id=f"room:{room_record.room_id}", action="INSERT", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Room created"})


@router.get("/rooms")
async def get_rooms(
    room_id: Optional[int] = Query(None),
    room_type_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    is_freezed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:READ"]),
):
    if room_id is not None:
        room_record = await svc_get_room(db, room_id)
        return RoomResponse.model_validate(room_record)

    cache_key = f"rooms:room_type:{room_type_id}:status:{status_filter}:is_freezed:{is_freezed}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    response_list = [Room.model_validate(r) for r in items]
    await set_cached(cache_key, response_list, ttl=120)
    return response_list


@router.put("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    room_record = await svc_update_room(db, room_id, payload)
    new_val = RoomResponse.model_validate(room_record).model_dump()
    await log_audit(entity="room", entity_id=f"room:{room_id}", action="UPDATE", new_value=new_val)
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Updated successfully"})


@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    await svc_delete_room(db, room_id)
    await invalidate_pattern("rooms:*")
    return {"message": "Room deleted"}


@router.post("/rooms/bulk-upload", response_model=BulkRoomUploadResponse, status_code=status.HTTP_200_OK)
async def bulk_upload_rooms(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    content = await file.read()
    result = await svc_bulk_upload_rooms(db, content)
    await invalidate_pattern("rooms:*")
    await log_audit(
        entity="room_bulk_upload",
        entity_id=f"bulk_upload:{result['successfully_created']}_rooms",
        action="INSERT",
        new_value=result,
    )
    return BulkRoomUploadResponse(**result)


# ==========================================================
# 🧩 AMENITIES SECTION
# ==========================================================
class RoomAmenityMapFlexible(BaseModel):
    room_id: int
    amenity_ids: List[int]


@router.post("/amenities", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(
    payload: AmenityCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    amenity_record = await svc_create_amenity(db, payload)
    new_val = AmenityResponse.model_validate(amenity_record).model_dump()
    await log_audit(entity="amenity", entity_id=f"amenity:{amenity_record.amenity_id}", action="INSERT", new_value=new_val)
    return AmenityResponse.model_validate(amenity_record).model_copy(update={"message": "Amenity created"})


@router.get("/amenities")
async def get_amenities(
    amenity_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if amenity_id:
        amenity_record = await svc_get_amenity(db, amenity_id)
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        return {
            "amenity": Amenity.model_validate(amenity_record).model_dump(),
            "rooms": [Room.model_validate(r).model_dump() for r in rooms],
        }
    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


@router.post("/rooms/{room_id}/amenities/map", status_code=status.HTTP_201_CREATED)
async def map_amenities_to_room(
    room_id: int,
    payload: RoomAmenityMapFlexible,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    amenity_ids = payload.amenity_ids
    if len(amenity_ids) == 1:
        single_payload = RoomAmenityMapCreate(room_id=room_id, amenity_id=amenity_ids[0])
        mapping = await svc_map_amenity(db, single_payload)
        await log_audit(entity="room_amenity", entity_id=f"room:{room_id}:amenity:{amenity_ids[0]}", action="INSERT")
        return RoomAmenityMapResponse.model_validate(mapping)

    result = await svc_map_amenities_bulk(db, room_id, amenity_ids)
    await log_audit(entity="room_amenity", entity_id=f"room:{room_id}", action="INSERT", new_value=result)
    return result


@router.get("/rooms/{room_id}/amenities")
async def get_amenities_for_room_endpoint(room_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc_get_amenities_for_room(db, room_id)
    return {"room_id": room_id, "amenities": [{"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in items]}


@router.delete("/rooms/{room_id}/amenities/unmap")
async def unmap_room_amenities(
    room_id: int,
    payload: RoomAmenityMapFlexible,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    amenity_ids = payload.amenity_ids
    if len(amenity_ids) == 1:
        await svc_unmap_amenity(db, room_id, amenity_ids[0])
        await log_audit(entity="room_amenity", entity_id=f"room:{room_id}:amenity:{amenity_ids[0]}", action="DELETE")
        return {"message": "Unmapped successfully"}
    result = await svc_unmap_amenities_bulk(db, room_id, amenity_ids)
    await log_audit(entity="room_amenity", entity_id=f"room:{room_id}", action="DELETE", new_value=result)
    return result


@router.delete("/amenities/{amenity_id}")
async def delete_amenity(
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    await svc_delete_amenity(db, amenity_id)
    await log_audit(entity="amenity", entity_id=f"amenity:{amenity_id}", action="DELETE")
    return {"message": "Amenity deleted"}
