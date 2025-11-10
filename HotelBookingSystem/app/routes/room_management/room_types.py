from fastapi import APIRouter, Depends, Security, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import RoomTypeCreate, RoomTypeResponse, RoomTypeUpdate
from app.dependencies.authentication import get_current_user, check_permission
from app.core.exceptions import ForbiddenError
from app.services.room_service.room_types_service import (
    create_room_type as svc_create_room_type,
    list_room_types as svc_list_room_types,
    get_room_type as svc_get_room_type,
    update_room_type as svc_update_room_type,
    soft_delete_room_type as svc_soft_delete_room_type,
)
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/room-types", tags=["ROOM_TYPES"])


# ============================================================================
# 🔹 CREATE - Add a new room type to the system
# ============================================================================
@router.post("/", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(
    payload: RoomTypeCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Create a new room type with ROOM_MANAGEMENT:WRITE permission."""
    room_type_record = await svc_create_room_type(db, payload)
    # audit create
    try:
        new_val = RoomTypeResponse.model_validate(room_type_record).model_dump()
        entity_id = f"room_type:{getattr(room_type_record, 'room_type_id', None)}"
        await log_audit(entity="room_type", entity_id=entity_id, action="INSERT", new_value=new_val)
    except Exception:
        pass
    # invalidate room-types cache
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(room_type_record).model_copy(update={"message": "Room type created"})


# ============================================================================
# 🔹 READ - Fetch room types (single or list)
# ============================================================================
@router.get("/")
async def get_room_types(
    room_type_id: Optional[int] = Query(None, description="If provided, returns the single room type with this ID"),
    include_deleted: Optional[bool] = Query(False),
    db: AsyncSession = Depends(get_db),
    # Require authentication for all users (basic users allowed)
    _current_user = Depends(get_current_user),
):
    """Single GET for room-types.

    - If `room_type_id` is provided, return the single RoomTypeResponse.
    - Otherwise return a list of RoomTypeResponse (filtered by include_deleted).
    Authentication required; basic users are allowed.
    """
    if room_type_id is not None:
        room_type_record = await svc_get_room_type(db, room_type_id)
        return RoomTypeResponse.model_validate(room_type_record)

    cache_key = f"room_types:include_deleted:{include_deleted}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_room_types(db, include_deleted=include_deleted)
    response_list = [RoomTypeResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in items]
    await set_cached(cache_key, response_list, ttl=300)
    return response_list


# ============================================================================
# 🔹 UPDATE - Modify existing room type details
# ============================================================================
@router.put("/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(
    room_type_id: int,
    payload: RoomTypeUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """Update room type with ROOM_MANAGEMENT:WRITE permission."""
    room_type_record = await svc_update_room_type(db, room_type_id, payload)
    # audit update
    try:
        new_val = RoomTypeResponse.model_validate(room_type_record).model_dump()
        entity_id = f"room_type:{getattr(room_type_record, 'room_type_id', None)}"
        await log_audit(entity="room_type", entity_id=entity_id, action="UPDATE", new_value=new_val)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(room_type_record).model_copy(update={"message": "Updated successfully"})


# ============================================================================
# 🔹 DELETE - Remove room type from system (soft delete)
# ============================================================================
@router.delete("/{room_type_id}")
async def soft_delete_room_type(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:DELETE"]),
):
    """Delete room type with ROOM_MANAGEMENT:DELETE permission."""
    await svc_soft_delete_room_type(db, room_type_id)
    await invalidate_pattern("room_types:*")
    return {"message": "Room type soft-deleted"}
