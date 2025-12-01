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
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer
from pydantic import BaseModel

# Pagination Response Model
class PaginatedResponse(BaseModel):
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

# Freeze Request Model
class FreezeRoomRequest(BaseModel):
    freeze_reason: Optional[str] = None

# Room Amenity Map Flexible Model
class RoomAmenityMapFlexible(BaseModel):
    amenity_ids: List[int]

# ==========================================================
# 🧩 Core Modules
# ==========================================================
from app.database.postgres_connection import get_db
from app.dependencies.authentication import check_permission, get_current_user
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit

# ==========================================================
# Helper function to convert SQLAlchemy model to dict
# Excludes lazy-loaded relationships to prevent greenlet errors
# ==========================================================
def to_dict_safe(obj, exclude_attrs=None):
    """Convert SQLAlchemy model to dict, excluding lazy attributes."""
    if exclude_attrs is None:
        exclude_attrs = {'amenities'}
    
    result = {}
    for col in obj.__table__.columns:
        result[col.name] = getattr(obj, col.name)
    return result

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
    update_amenity as svc_update_amenity,
    map_amenity as svc_map_amenity,
    get_rooms_for_amenity as svc_get_rooms_for_amenity,
    get_amenities_for_room as svc_get_amenities_for_room,
    unmap_amenity as svc_unmap_amenity,
    map_amenities_bulk as svc_map_amenities_bulk,
    unmap_amenities_bulk as svc_unmap_amenities_bulk,
)

# CRUD utilities
from app.crud.rooms import fetch_rooms_filtered

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
    room_type_name: str = Form(...),
    price_per_night: float = Form(...),
    occupancy_limit_adults: int = Form(...),
    occupancy_limit_children: int = Form(0),
    square_ft: int = Form(50),
    description: str = Form(""),
    amenities: str = Form("[]"),  # JSON array string
    images: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Create a new room type with amenities and images"""
    import json
    from app.core.cloudinary import cloudinary_client
    
    
    try:
        amenity_ids = json.loads(amenities) if amenities != "[]" else []
    except:
        amenity_ids = []
    
    # Upload images to Cloudinary if provided
    image_urls = []
    if images:
        for image in images:
            if image.filename:
                try:
                    result = cloudinary_client.uploader.upload(
                        image.file,
                        folder="luxury-stay/room-types",
                        resource_type="auto"
                    )
                    image_urls.append(result.get('secure_url', ''))
                except Exception as e:
                    print(f"Image upload failed: {e}")
    
    # Create RoomTypeCreate with mapped field names
    payload = RoomTypeCreate(
        room_type_name=room_type_name,
        price_per_night=price_per_night,
        occupancy_limit_adults=occupancy_limit_adults,
        occupancy_limit_children=occupancy_limit_children,
        square_ft=square_ft,
        description=description,
        amenities=amenity_ids
    )
    
    room_type_record = await svc_create_room_type(db, payload)
    
    # Save images to database if any were uploaded to Cloudinary
    if image_urls:
        for idx, image_url in enumerate(image_urls):
            try:
                await create_image(
                    db,
                    entity_type="room_type",
                    entity_id=room_type_record.room_type_id,
                    image_url=image_url,
                    caption=None,
                    is_primary=(idx == 0),  # First image is primary
                    uploaded_by=current_user.user_id,
                )
            except Exception as e:
                print(f"Failed to save image record to database: {e}")
    
    # Eagerly load relationships
    await db.refresh(room_type_record, ["rooms"])
    
    try:
        room_type_dict = to_dict_safe(room_type_record)
        new_val = RoomTypeResponse.model_validate(room_type_dict).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_record.room_type_id}", action="INSERT", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    room_type_dict = to_dict_safe(room_type_record)
    return RoomTypeResponse.model_validate(room_type_dict).model_copy(update={"message": "Room type created"})


@router.get("/types", response_model=List[RoomTypeResponse])
async def get_room_types(
    room_type_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    if room_type_id is not None:
        room_type_record = await svc_get_room_type(db, room_type_id)
        room_type_dict = to_dict_safe(room_type_record)
        return [RoomTypeResponse.model_validate(room_type_dict)]

    cache_key = "room_types:all"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    items = await svc_list_room_types(db)
    response_list = [RoomTypeResponse.model_validate(to_dict_safe(r)).model_copy(update={"message": "Fetched successfully"}) for r in items]
    await set_cached(cache_key, response_list, ttl=300)
    return response_list


@router.get("/types/{room_type_id}", response_model=RoomTypeResponse)
async def get_room_type_by_id(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:READ"]),
):
    """Fetch a single room type by ID"""
    room_type_record = await svc_get_room_type(db, room_type_id)
    room_type_dict = to_dict_safe(room_type_record)
    return RoomTypeResponse.model_validate(room_type_dict)


@router.put("/types/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(
    room_type_id: int,
    payload: RoomTypeUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    room_type_record = await svc_update_room_type(db, room_type_id, payload)
    try:
        room_type_dict = to_dict_safe(room_type_record)
        new_val = RoomTypeResponse.model_validate(room_type_dict).model_dump()
        await log_audit(entity="room_type", entity_id=f"room_type:{room_type_id}", action="UPDATE", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    room_type_dict = to_dict_safe(room_type_record)
    return RoomTypeResponse.model_validate(room_type_dict).model_copy(update={"message": "Updated successfully"})


@router.delete("/types/{room_type_id}")
async def soft_delete_room_type(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"]),
):
    await svc_soft_delete_room_type(db, room_type_id)
    await invalidate_pattern("room_types:*")
    return {"message": "Room type soft-deleted"}


@router.get("/types/{room_type_id}/amenities")
async def get_amenities_for_room_type(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all amenities for a specific room type"""
    from app.crud.rooms import fetch_amenities_by_room_type_id
    amenities = await fetch_amenities_by_room_type_id(db, room_type_id)
    return {
        "room_type_id": room_type_id,
        "amenities": [{"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in amenities]
    }


@router.post("/types/{room_type_id}/amenities/update", status_code=status.HTTP_200_OK)
async def update_room_type_amenities(
    room_type_id: int,
    payload: RoomAmenityMapFlexible,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """
    Update amenities for a room type.
    Directly maps/unmaps amenities to/from the room type (not individual rooms).
    """
    from app.crud.rooms import (
        fetch_amenities_by_room_type_id,
        insert_room_type_amenity_map,
        delete_all_amenities_for_room_type
    )
    
    selected_amenity_ids = payload.amenity_ids
    print(f"[UPDATE_AMENITIES] Room Type ID: {room_type_id}, Selected IDs: {selected_amenity_ids}")
    
    # Get existing amenities for this room type
    existing_amenities = await fetch_amenities_by_room_type_id(db, room_type_id)
    existing_amenity_ids = [a.amenity_id for a in existing_amenities]
    print(f"[UPDATE_AMENITIES] Existing IDs: {existing_amenity_ids}")
    
    # Find amenities to add (selected but not existing)
    amenities_to_add = [aid for aid in selected_amenity_ids if aid not in existing_amenity_ids]
    
    # Find amenities to remove (existing but not selected)
    amenities_to_remove = [aid for aid in existing_amenity_ids if aid not in selected_amenity_ids]
    print(f"[UPDATE_AMENITIES] To Add: {amenities_to_add}, To Remove: {amenities_to_remove}")
    
    results = []
    
    # Map new amenities directly to room type
    for amenity_id in amenities_to_add:
        try:
            await insert_room_type_amenity_map(db, {
                'room_type_id': room_type_id,
                'amenity_id': amenity_id
            })
            await db.flush()  # Flush after each insert to ensure it's processed
            results.append({"amenity_id": amenity_id, "action": "mapped", "status": "success"})
            await log_audit(
                entity="room_type_amenity",
                entity_id=f"room_type:{room_type_id}:amenity:{amenity_id}",
                action="INSERT"
            )
        except Exception as e:
            print(f"Error mapping amenity {amenity_id}: {str(e)}")  # Debug log
            results.append({"amenity_id": amenity_id, "action": "mapped", "status": "failed", "error": str(e)})
    
    # Unmap removed amenities from room type
    for amenity_id in amenities_to_remove:
        try:
            from app.crud.rooms import delete_room_type_amenity_map
            await delete_room_type_amenity_map(db, room_type_id, amenity_id)
            await db.flush()  # Flush after each delete to ensure it's processed
            results.append({"amenity_id": amenity_id, "action": "unmapped", "status": "success"})
            print(f"[DELETE_SUCCESS] Deleted amenity {amenity_id} from room type {room_type_id}")
            await log_audit(
                entity="room_type_amenity",
                entity_id=f"room_type:{room_type_id}:amenity:{amenity_id}",
                action="DELETE"
            )
        except Exception as e:
            print(f"Error unmapping amenity {amenity_id}: {str(e)}")  # Debug log
            results.append({"amenity_id": amenity_id, "action": "unmapped", "status": "failed", "error": str(e)})
    
    await db.commit()
    await invalidate_pattern("room_types:*")
    print(f"[UPDATE_AMENITIES] Commit successful. Results: {results}")
    
    return {
        "room_type_id": room_type_id,
        "amenities_updated": len(results),
        "results": results
    }


@router.get("/room-types", response_model=List[RoomTypeResponse])
async def list_room_types_public(
    db: AsyncSession = Depends(get_db),
    _current_user: Users = Depends(get_current_user),
):
    """
    Get all room types (public endpoint for dropdowns, requires auth).
    """
    cache_key = "room_types:public:all"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    items = await svc_list_room_types(db)
    response_list = [RoomTypeResponse.model_validate(to_dict_safe(r)) for r in items]
    await set_cached(cache_key, response_list, ttl=300)
    return response_list


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
    # Eagerly load the room_type relationship
    await db.refresh(room_record, ["room_type"])
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
    skip: int = Query(0, ge=0, description="Number of rooms to skip (pagination offset)"),
    limit: int = Query(10, ge=1, le=100, description="Number of rooms to return (pagination limit)"),
    sort_by: str = Query("room_id", description="Column to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    _current_user = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
):
    if room_id is not None:
        room_record = await svc_get_room(db, room_id)
        return RoomResponse.model_validate(room_record)

    cache_key = f"rooms:room_type:{room_type_id}:status:{status_filter}:is_freezed:{is_freezed}:skip:{skip}:limit:{limit}:sort_by:{sort_by}:sort_order:{sort_order}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    
    # Apply sorting
    sort_column_map = {
        'room_id': 'room_id',
        'room_no': 'room_no',
        'room_type_id': 'room_type_id',
        'room_status': 'room_status',
        'price_per_night': 'room_type.price_per_night'
    }
    
    sort_key = sort_column_map.get(sort_by, 'room_id')
    reverse = sort_order.lower() == 'desc'
    
    # Handle nested sorting for price_per_night
    if sort_key == 'room_type.price_per_night':
        items = sorted(items, key=lambda x: x.room_type.price_per_night if x.room_type else 0, reverse=reverse)
    else:
        items = sorted(items, key=lambda x: getattr(x, sort_key, ''), reverse=reverse)
    
    # Calculate total count before pagination
    total_count = len(items)
    
    # Apply pagination
    paginated_items = items[skip:skip + limit]
    
    # Calculate page number and total pages
    page = (skip // limit) + 1 if limit > 0 else 1
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
    
    response_list = [RoomResponse.model_validate(r) for r in paginated_items]
    
    # Create paginated response
    paginated_response = {
        "data": response_list,
        "total": total_count,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages
    }
    
    await set_cached(cache_key, paginated_response, ttl=120)
    return paginated_response


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room_by_id(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
):
    """Get a single room by ID"""
    cache_key = f"rooms:single:{room_id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    room_record = await svc_get_room(db, room_id)
    if not room_record:
        raise HTTPException(status_code=404, detail=f"Room with ID {room_id} not found")
    
    response = RoomResponse.model_validate(room_record)
    await set_cached(cache_key, response.model_dump(), ttl=120)
    return response



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


@router.post("/rooms/{room_id}/freeze")
async def freeze_room(
    room_id: int,
    payload: FreezeRoomRequest,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Freeze a room with an optional reason"""
    from app.models.sqlalchemy_schemas.rooms import FreezeReason
    
    room_record = await svc_get_room(db, room_id)
    if not room_record:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Map user's free-form reason to enum value
    # If user provides a reason, use ADMIN_LOCK, otherwise use SYSTEM_HOLD
    freeze_reason_enum = FreezeReason.ADMIN_LOCK if payload.freeze_reason else FreezeReason.SYSTEM_HOLD
    
    # Update room status to FROZEN and set freeze reason
    room_record.room_status = "FROZEN"
    room_record.freeze_reason = freeze_reason_enum
    db.add(room_record)
    await db.commit()
    await db.refresh(room_record)
    
    # Log audit with the user's reason as context
    new_val = RoomResponse.model_validate(room_record).model_dump()
    new_val['user_freeze_reason'] = payload.freeze_reason or "Auto-frozen"
    await log_audit(entity="room", entity_id=f"room:{room_id}", action="FREEZE", new_value=new_val)
    await invalidate_pattern("rooms:*")
    
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Room frozen successfully"})


@router.delete("/rooms/{room_id}/freeze")
async def unfreeze_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Unfreeze a room"""
    from app.models.sqlalchemy_schemas.rooms import FreezeReason
    
    room_record = await svc_get_room(db, room_id)
    if not room_record:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update room status to AVAILABLE and clear freeze reason
    room_record.room_status = "AVAILABLE"
    room_record.freeze_reason = FreezeReason.NONE
    db.add(room_record)
    await db.commit()
    await db.refresh(room_record)
    
    # Log audit
    new_val = RoomResponse.model_validate(room_record).model_dump()
    await log_audit(entity="room", entity_id=f"room:{room_id}", action="UNFREEZE", new_value=new_val)
    await invalidate_pattern("rooms:*")
    
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Room unfrozen successfully"})


@router.post("/rooms/bulk-upload", response_model=BulkRoomUploadResponse, status_code=status.HTTP_200_OK)
async def bulk_upload_rooms(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    content = await file.read()
    result = await svc_bulk_upload_rooms(db, content, filename=file.filename or "")
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


@router.put("/amenities/{amenity_id}", response_model=AmenityResponse)
async def update_amenity(
    amenity_id: int,
    payload: AmenityCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    amenity_record = await svc_update_amenity(db, amenity_id, payload)
    new_val = AmenityResponse.model_validate(amenity_record).model_dump()
    await log_audit(entity="amenity", entity_id=f"amenity:{amenity_id}", action="UPDATE", new_value=new_val)
    return AmenityResponse.model_validate(amenity_record).model_copy(update={"message": "Amenity updated"})


@router.delete("/amenities/{amenity_id}")
async def delete_amenity(
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    await svc_delete_amenity(db, amenity_id)
    await log_audit(entity="amenity", entity_id=f"amenity:{amenity_id}", action="DELETE")
    return {"message": "Amenity deleted"}


@router.delete("/amenities/{amenity_id}/rooms/{room_id}")
async def unmap_amenity_from_room(
    amenity_id: int,
    room_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Unmap a specific amenity from a specific room"""
    try:
        await svc_unmap_amenity(db, room_id, amenity_id)
        await log_audit(
            entity="room_amenity",
            entity_id=f"room:{room_id}:amenity:{amenity_id}",
            action="DELETE",
            new_value={"status": "unmapped"}
        )
        return {"message": "Amenity unmapped from room"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unmap amenity: {str(e)}"
        )


# ==========================================================
# 📊 Dashboard KPI Endpoints
# ==========================================================

@router.get("/dashboard/kpis")
async def get_dashboard_kpis(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get dashboard KPIs: total room types, active rooms, available rooms, frozen rooms, revenue"""
    from sqlalchemy import func, select, case
    from app.models.sqlalchemy_schemas.rooms import RoomTypes, Rooms as RoomModel, RoomStatus
    
    cache_key = "dashboard_kpis"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    try:
        # Total Room Types
        total_types_query = select(func.count(RoomTypes.room_type_id))
        total_types_result = await db.execute(total_types_query)
        total_types = total_types_result.scalar() or 0
        
        # Total Active Rooms (not frozen)
        active_rooms_query = select(func.count(RoomModel.room_id)).where(
            RoomModel.room_status != RoomStatus.FROZEN
        )
        active_rooms_result = await db.execute(active_rooms_query)
        active_rooms = active_rooms_result.scalar() or 0
        
        # Available Rooms
        available_rooms_query = select(func.count(RoomModel.room_id)).where(
            RoomModel.room_status == RoomStatus.AVAILABLE
        )
        available_rooms_result = await db.execute(available_rooms_query)
        available_rooms = available_rooms_result.scalar() or 0
        
        # Frozen Rooms
        frozen_rooms_query = select(func.count(RoomModel.room_id)).where(
            RoomModel.room_status == RoomStatus.FROZEN
        )
        frozen_rooms_result = await db.execute(frozen_rooms_query)
        frozen_rooms = frozen_rooms_result.scalar() or 0
        
        # Total Revenue (sum of price_per_night for all room types)
        revenue_query = select(func.sum(RoomTypes.price_per_night))
        revenue_result = await db.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0
        
        response = {
            "total_types": total_types,
            "active_rooms": active_rooms,
            "available_rooms": available_rooms,
            "frozen_rooms": frozen_rooms,
            "total_revenue": float(total_revenue)
        }
        
        await set_cached(cache_key, response, ttl=300)
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard KPIs: {str(e)}"
        )


@router.get("/room-types/with-stats")
async def get_room_types_with_stats(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get all room types with room counts and statistics"""
    from sqlalchemy import func, select
    from app.models.sqlalchemy_schemas.rooms import RoomTypes, Rooms as RoomModel, RoomStatus
    
    cache_key = "room_types_with_stats"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    # Join room types with rooms and count by status
    stmt = select(
        RoomTypes,
        func.count(RoomModel.room_id).label("total_count"),
        func.sum(
            func.cast(
                RoomModel.room_status == RoomStatus.AVAILABLE,
                Integer
            )
        ).label("available_count"),
        func.sum(
            func.cast(
                RoomModel.room_status == RoomStatus.BOOKED,
                Integer
            )
        ).label("booked_count"),
        func.sum(
            func.cast(
                RoomModel.room_status == RoomStatus.FROZEN,
                Integer
            )
        ).label("frozen_count"),
        func.sum(
            func.cast(
                RoomModel.room_status == RoomStatus.MAINTENANCE,
                Integer
            )
        ).label("maintenance_count"),
    ).outerjoin(
        RoomModel,
        RoomTypes.room_type_id == RoomModel.room_type_id
    ).group_by(RoomTypes.room_type_id)
    
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    room_types_list = []
    for row in rows:
        room_type_record = row[0]
        room_type_dict = to_dict_safe(room_type_record)
        room_type_dict = RoomTypeResponse.model_validate(room_type_dict).model_dump()
        room_type_dict['totalCount'] = row[1] or 0
        room_type_dict['availableCount'] = row[2] or 0
        room_type_dict['bookedCount'] = row[3] or 0
        room_type_dict['frozenCount'] = row[4] or 0
        room_type_dict['maintenanceCount'] = row[5] or 0
        room_types_list.append(room_type_dict)
    
    await set_cached(cache_key, room_types_list, ttl=300)
    return room_types_list



async def get_room_kpis(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get room management KPIs"""
    cache_key = "room_kpis"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    from sqlalchemy import func, select
    from app.models.sqlalchemy_schemas.rooms import Rooms as RoomModel
    
    # Total room types
    room_types = await svc_list_room_types(db)
    total_types = len(room_types)
    
    # Room status counts
    stmt = select(
        RoomModel.room_status,
        func.count(RoomModel.room_id).label("count")
    ).group_by(RoomModel.room_status)
    
    result = await db.execute(stmt)
    status_counts = {str(row[0].value) if hasattr(row[0], 'value') else str(row[0]): row[1] for row in result.fetchall()}
    
    # Calculate metrics
    active_rooms = sum([count for status, count in status_counts.items() if status != 'MAINTENANCE'])
    frozen_rooms = status_counts.get('FROZEN', 0)
    available_rooms = status_counts.get('AVAILABLE', 0)
    total_revenue = 0  # Will be calculated from bookings if needed
    
    kpis = {
        "totalTypes": total_types,
        "activeRooms": active_rooms,
        "frozenRooms": frozen_rooms,
        "availableRooms": available_rooms,
        "totalRevenue": total_revenue,
        "statusCounts": status_counts
    }
    
    await set_cached(cache_key, kpis, ttl=300)
    return kpis


@router.get("/amenities/{amenity_id}/rooms")
async def get_rooms_by_amenity(
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get all rooms that have a specific amenity"""
    try:
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        if not rooms:
            return []
        
        # Convert ORM objects to dictionaries
        rooms_list = []
        for room in rooms:
            room_dict = {
                "room_id": room.room_id,
                "room_no": room.room_no,
                "room_type_id": room.room_type_id,
                "room_status": room.room_status.value if hasattr(room.room_status, 'value') else str(room.room_status),
                "freeze_reason": room.freeze_reason.value if room.freeze_reason and hasattr(room.freeze_reason, 'value') else (str(room.freeze_reason) if room.freeze_reason else None),
                "created_at": room.created_at,
                "updated_at": room.updated_at,
                "is_deleted": room.is_deleted
            }
            rooms_list.append(room_dict)
        
        return rooms_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rooms for amenity: {str(e)}"
        )


@router.get("/amenities/with-room-count")
async def get_amenities_with_room_count(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get all amenities with count of actual rooms they're in"""
    from sqlalchemy import func, select
    from app.models.sqlalchemy_schemas.rooms import RoomAmenities, RoomTypeAmenityMap, RoomTypes, Rooms
    
    cache_key = "amenities_with_count"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    # Join: Amenities -> RoomTypeAmenityMap -> RoomTypes -> Rooms and count rooms
    # Use outer join so amenities with no rooms still appear (with count 0)
    from sqlalchemy import case
    
    stmt = select(
        RoomAmenities,
        func.count(
            case(
                (Rooms.is_deleted.is_(False), Rooms.room_id),
                else_=None
            )
        ).label("room_count")
    ).outerjoin(
        RoomTypeAmenityMap,
        RoomAmenities.amenity_id == RoomTypeAmenityMap.amenity_id
    ).outerjoin(
        RoomTypes,
        RoomTypeAmenityMap.room_type_id == RoomTypes.room_type_id
    ).outerjoin(
        Rooms,
        RoomTypes.room_type_id == Rooms.room_type_id
    ).group_by(RoomAmenities.amenity_id)
    
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    amenities_list = []
    for amenity_record, room_count in rows:
        amenity_dict = Amenity.model_validate(amenity_record).model_dump()
        amenity_dict['roomCount'] = room_count or 0
        amenities_list.append(amenity_dict)
    
    await set_cached(cache_key, amenities_list, ttl=300)
    return amenities_list


# ==========================================================
# 🧩 BULK UPLOAD TEMPLATE
# ==========================================================
@router.get("/rooms/bulk-upload/template")
async def get_bulk_upload_template():
    """Download CSV template for bulk room upload"""
    from io import StringIO
    import csv
    
    # Create CSV in memory with BOTH options (room_type_id OR room_type_name)
    output = StringIO()
    writer = csv.writer(output)
    
    # Header row - showing both options available
    writer.writerow([
        "room_no",
        "room_type_id",
        "room_status",
        "freeze_reason"
    ])
    
    # Example rows using room_type_id (can also use room_type_name instead)
    writer.writerow([
        "101",
        "1",
        "AVAILABLE",
        "NONE"
    ])
    writer.writerow([
        "102",
        "1",
        "AVAILABLE",
        "NONE"
    ])
    writer.writerow([
        "201",
        "2",
        "AVAILABLE",
        "NONE"
    ])
    
    csv_content = output.getvalue()
    
    return {
        "status": "success",
        "template": csv_content,
        "instructions": {
            "room_no": "Unique room number/identifier (required, max 20 chars)",
            "room_type_id_or_name": "Either room_type_id (integer ID) OR room_type_name (string name) - required, at least one must be provided",
            "room_type_id": "Integer ID of the room type (required if room_type_name not provided)",
            "room_type_name": "String name of the room type (required if room_type_id not provided)",
            "room_status": "Room status - AVAILABLE, BOOKED, MAINTENANCE, or FROZEN (optional, defaults to AVAILABLE)",
            "freeze_reason": "Reason if frozen - NONE, CLEANING, ADMIN_LOCK, or SYSTEM_HOLD (optional, defaults to NONE)"
        },
        "examples": {
            "using_id": {
                "room_no": "101",
                "room_type_id": "1",
                "room_status": "AVAILABLE",
                "freeze_reason": "NONE"
            },
            "using_name": {
                "room_no": "101",
                "room_type_name": "Deluxe",
                "room_status": "AVAILABLE",
                "freeze_reason": "NONE"
            }
        }
    }

