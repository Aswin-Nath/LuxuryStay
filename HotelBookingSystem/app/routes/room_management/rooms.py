from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.room import RoomCreate, RoomResponse, Room, RoomUpdate
from app.dependencies.authentication import get_user_permissions, get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.room_service.rooms_service import (
    create_room as svc_create_room,
    list_rooms as svc_list_rooms,
    get_room as svc_get_room,
    update_room as svc_update_room,
    delete_room as svc_delete_room,
)

router = APIRouter(prefix="/api/rooms", tags=["ROOMS"])


def _require_permissions(user_permissions: dict, required_resources: list, perm: PermissionTypes, require_all: bool = True):
    """Simple helper to validate permissions.

    - required_resources: list of Resources to check
    - perm: PermissionTypes (READ/WRITE)
    - require_all: if True, user must have the permission on all required resources; if False, any one suffices
    """
    # Normalize required resources and permission to strings (enum.value)
    req_keys = [r.value if hasattr(r, 'value') else str(r).upper() for r in required_resources]
    perm_key = perm.value if hasattr(perm, 'value') else str(perm).upper()

    satisfied = 0
    for res_key, perms in user_permissions.items():
        if res_key in req_keys and perm_key in perms:
            satisfied += 1
    if require_all and satisfied < len(required_resources):
        raise ForbiddenError("Insufficient permissions")
    if not require_all and satisfied == 0:
        raise ForbiddenError("Insufficient permissions")


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    obj = await svc_create_room(db, payload)
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Room created"})


@router.get("/")
async def get_rooms(
    # If client provides room_id as query param, return single room. Otherwise return list filtered by other params.
    room_id: Optional[int] = Query(None, description="If provided, returns the single room with this ID"),
    room_type_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    is_freezed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    # Authenticate user first, then ensure they are not a basic user (admins/managers allowed)
    _current_user = Depends(get_current_user),
    _ok: bool = Depends(ensure_not_basic_user),
):
    """Single GET endpoint for rooms.

    Behavior:
    - If `room_id` is provided: return the single room as `RoomResponse`.
    - Otherwise: return a list of `Room` matching optional filters.

    Access control: only non-basic users (admins/managers) may access this endpoint.
    """
    if room_id is not None:
        obj = await svc_get_room(db, room_id)
        return RoomResponse.model_validate(obj)

    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    return [Room.model_validate(r) for r in items]


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, payload: RoomUpdate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    obj = await svc_update_room(db, room_id, payload)
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    await svc_delete_room(db, room_id)
    return {"message": "Room deleted"}
