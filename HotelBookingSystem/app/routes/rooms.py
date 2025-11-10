from fastapi import (
    APIRouter, Depends, Security, status, Query, UploadFile, File, Form, HTTPException
)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database.postgres_connection import get_db
from app.dependencies.authentication import (
    check_permission,
    get_current_user,
)
from app.models.sqlalchemy_schemas.users import Users
from app.core.exceptions import ForbiddenException
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_util import log_audit

# ====================================================================
# 🧩 IMPORT SERVICE MODULES
# ====================================================================
from app.services.room_service.room_types_service import (
    create_room_type as svc_create_room_type,
    list_room_types as svc_list_room_types,
    get_room_type as svc_get_room_type,
    update_room_type as svc_update_room_type,
    soft_delete_room_type as svc_soft_delete_room_type,
)
from app.services.room_service.rooms_service import (
    create_room as svc_create_room,
    list_rooms as svc_list_rooms,
    get_room as svc_get_room,
    update_room as svc_update_room,
    delete_room as svc_delete_room,
    bulk_upload_rooms as svc_bulk_upload_rooms,
)
from app.services.room_service.amenities_service import (
    create_amenity as svc_create_amenity,
    list_amenities as svc_list_amenities,
    get_amenity as svc_get_amenity,
    delete_amenity as svc_delete_amenity,
)
from app.services.room_service.room_amenities_service import (
    map_amenity as svc_map_amenity,
    get_rooms_for_amenity as svc_get_rooms_for_amenity,
    get_amenities_for_room as svc_get_amenities_for_room,
    unmap_amenity as svc_unmap_amenity,
    map_amenities_bulk as svc_map_amenities_bulk,
    unmap_amenities_bulk as svc_unmap_amenities_bulk,
)
from app.services.image_upload_service import save_uploaded_image
from app.utils.images_util import (
    create_image,
    get_images_for_room,
    hard_delete_image,
    set_image_primary,
)

# ====================================================================
# 🧩 IMPORT SCHEMAS
# ====================================================================
from app.schemas.pydantic_models.room import (
    RoomTypeCreate, RoomTypeResponse, RoomTypeUpdate,
    RoomCreate, RoomResponse, Room, RoomUpdate, BulkRoomUploadResponse,
    AmenityCreate, AmenityResponse, Amenity,
    RoomAmenityMapCreate, RoomAmenityMapResponse
)
from app.schemas.pydantic_models.images import ImageResponse

# ====================================================================
# 📘 MAIN ROUTER COMPOSITION
# ====================================================================
router = APIRouter(prefix="/rooms", tags=["ROOM_MANAGEMENT"])

# ====================================================================
# 🏷️ ROOM TYPES ENDPOINTS
# ====================================================================

@router.post("/types", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    room_type_record = await svc_create_room_type(db, payload)
    try:
        new_val = RoomTypeResponse.model_validate(room_type_record).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_record.room_type_id}", action="INSERT", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(room_type_record).model_copy(update={"message": "Room type created"})


@router.get("/types")
async def get_room_types(room_type_id: Optional[int] = Query(None), include_deleted: Optional[bool] = Query(False), db: AsyncSession = Depends(get_db), _current_user = Depends(get_current_user)):
    if room_type_id is not None:
        record = await svc_get_room_type(db, room_type_id)
        return RoomTypeResponse.model_validate(record)
    cache_key = f"room_types:include_deleted:{include_deleted}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    items = await svc_list_room_types(db, include_deleted=include_deleted)
    response = [RoomTypeResponse.model_validate(r) for r in items]
    await set_cached(cache_key, response, ttl=300)
    return response


@router.put("/types/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(room_type_id: int, payload: RoomTypeUpdate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    record = await svc_update_room_type(db, room_type_id, payload)
    try:
        new_val = RoomTypeResponse.model_validate(record).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_id}", action="UPDATE", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(record).model_copy(update={"message": "Updated successfully"})


@router.delete("/types/{room_type_id}")
async def delete_room_type(room_type_id: int, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"])):
    await svc_soft_delete_room_type(db, room_type_id)
    await invalidate_pattern("room_types:*")
    return {"message": "Room type soft-deleted"}


# ====================================================================
# 🏷️ ROOMS ENDPOINTS
# ====================================================================

@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    record = await svc_create_room(db, payload)
    try:
        await log_audit(entity="room", entity_id=f"room:{record.room_id}", action="INSERT", new_value=RoomResponse.model_validate(record).model_dump())
    except Exception:
        pass
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(record).model_copy(update={"message": "Room created"})


@router.get("/")
async def get_rooms(
    room_id: Optional[int] = Query(None),
    room_type_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    is_freezed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:READ"]),
):
    if room_id:
        return RoomResponse.model_validate(await svc_get_room(db, room_id))
    cache_key = f"rooms:room_type:{room_type_id}:status:{status_filter}:is_freezed:{is_freezed}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    response = [Room.model_validate(r) for r in items]
    await set_cached(cache_key, response, ttl=120)
    return response


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, payload: RoomUpdate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE", "BOOKING:WRITE"])):
    record = await svc_update_room(db, room_id, payload)
    try:
        await log_audit(entity="room", entity_id=f"room:{room_id}", action="UPDATE", new_value=RoomResponse.model_validate(record).model_dump())
    except Exception:
        pass
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(record).model_copy(update={"message": "Updated successfully"})


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE", "BOOKING:WRITE"])):
    await svc_delete_room(db, room_id)
    await invalidate_pattern("rooms:*")
    return {"message": "Room deleted"}


@router.post("/bulk-upload", response_model=BulkRoomUploadResponse)
async def bulk_upload_rooms(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE", "BOOKING:WRITE"]),
):
    content = await file.read()
    result = await svc_bulk_upload_rooms(db, content)
    await invalidate_pattern("rooms:*")
    try:
        await log_audit(entity="room_bulk_upload", entity_id=f"bulk_upload:{result['successfully_created']}_rooms", action="INSERT", new_value=result)
    except Exception:
        pass
    return BulkRoomUploadResponse(**result)

# ====================================================================
# 🏷️ AMENITIES ENDPOINTS
# ====================================================================

class RoomAmenityMapFlexible(BaseModel):
    room_id: int
    amenity_ids: List[int]


@router.post("/amenities", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(payload: AmenityCreate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    record = await svc_create_amenity(db, payload)
    try:
        await log_audit(entity="amenity", entity_id=f"amenity:{record.amenity_id}", action="INSERT", new_value=AmenityResponse.model_validate(record).model_dump())
    except Exception:
        pass
    return AmenityResponse.model_validate(record).model_copy(update={"message": "Amenity created"})


@router.get("/amenities")
async def get_amenities(amenity_id: Optional[int] = Query(None), db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    if amenity_id:
        amenity_record = await svc_get_amenity(db, amenity_id)
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        return {"amenity": Amenity.model_validate(amenity_record).model_dump(), "rooms": [Room.model_validate(r).model_dump() for r in rooms]}
    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


@router.post("/amenities/map")
async def map_amenities(payload: RoomAmenityMapFlexible, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    if len(payload.amenity_ids) == 1:
        amenity_mapping_record = await svc_map_amenity(db, RoomAmenityMapCreate(room_id=payload.room_id, amenity_id=payload.amenity_ids[0]))
        return RoomAmenityMapResponse.model_validate(amenity_mapping_record).model_copy(update={"message": "Mapped successfully"})
    mapping_response = await svc_map_amenities_bulk(db, payload.room_id, payload.amenity_ids)
    return mapping_response


@router.delete("/amenities/unmap")
async def unmap_amenities(payload: RoomAmenityMapFlexible, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    if len(payload.amenity_ids) == 1:
        await svc_unmap_amenity(db, payload.room_id, payload.amenity_ids[0])
        return {"message": "Unmapped successfully"}
    result = await svc_unmap_amenities_bulk(db, payload.room_id, payload.amenity_ids)
    return result


@router.get("/amenities/room/{room_id}")
async def get_amenities_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc_get_amenities_for_room(db, room_id)
    return {"room_id": room_id, "amenities": [{"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in items]}


@router.delete("/amenities/{amenity_id}")
async def delete_amenity(amenity_id: int, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    await svc_delete_amenity(db, amenity_id)
    return {"message": "Amenity deleted"}


# ====================================================================
# 🏷️ ROOM IMAGES ENDPOINTS
# ====================================================================

@router.post("/{room_id}/images", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image_for_room(room_id: int, image: UploadFile = File(...), caption: Optional[str] = Form(None), is_primary: Optional[bool] = Form(False), db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    try:
        image_url = await save_uploaded_image(image)
        image_record = await create_image(db, entity_type="room_type", entity_id=room_id, image_url=image_url, caption=caption, is_primary=is_primary, uploaded_by=current_user.user_id)
        return ImageResponse.model_validate(image_record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{room_id}/images", response_model=List[ImageResponse])
async def list_images_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    items = await get_images_for_room(db, room_id)
    return [ImageResponse.model_validate(i) for i in items]


@router.delete("/{room_id}/images")
async def delete_images_for_room(image_ids: List[int] = Query(...), db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"])):
    for image_id in image_ids:
        await hard_delete_image(db, image_id, requester_id=current_user.user_id)
    return {"message": "images deleted"}


@router.put("/{room_id}/images/{image_id}/primary")
async def mark_image_primary(image_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"])):
    await set_image_primary(db, image_id, requester_id=current_user.user_id)
    return {"message": "Image marked as primary"}
