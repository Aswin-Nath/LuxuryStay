from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import RoomTypeCreate, RoomTypeResponse, RoomTypeUpdate
from app.dependencies.authentication import get_user_permissions, get_current_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
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


@router.post("/", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Permission check: require room_service.WRITE
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to create room types")

    obj = await svc_create_room_type(db, payload)
    # audit create
    try:
        new_val = RoomTypeResponse.model_validate(obj).model_dump()
        entity_id = f"room_type:{getattr(obj, 'room_type_id', None)}"
        changed_by = getattr(locals().get('current_user'), 'user_id', None) or getattr(payload, 'user_id', None)
        await log_audit(entity="room_type", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
    except Exception:
        pass
    # invalidate room-types cache
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Room type created"})


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
        obj = await svc_get_room_type(db, room_type_id)
        return RoomTypeResponse.model_validate(obj)

    cache_key = f"room_types:include_deleted:{include_deleted}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_room_types(db, include_deleted=include_deleted)
    result = [RoomTypeResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in items]
    await set_cached(cache_key, result, ttl=300)
    return result


@router.put("/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(room_type_id: int, payload: RoomTypeUpdate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to update room types")

    obj = await svc_update_room_type(db, room_type_id, payload)
    # audit update
    try:
        new_val = RoomTypeResponse.model_validate(obj).model_dump()
        entity_id = f"room_type:{getattr(obj, 'room_type_id', None)}"
        changed_by = getattr(locals().get('current_user'), 'user_id', None)
        await log_audit(entity="room_type", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
    except Exception:
        pass
    await invalidate_pattern("room_types:*")
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.delete("/{room_type_id}")
async def soft_delete_room_type(room_type_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete room types")

    await svc_soft_delete_room_type(db, room_type_id)
    await invalidate_pattern("room_types:*")
    return {"message": "Room type soft-deleted"}
