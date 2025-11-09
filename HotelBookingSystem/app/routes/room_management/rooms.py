from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import (
    RoomCreate, RoomResponse, Room, RoomUpdate, BulkRoomUploadResponse
)
from app.dependencies.authentication import get_user_permissions, get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.room_service.rooms_service import (
    create_room as svc_create_room,
    list_rooms as svc_list_rooms,
    get_room as svc_get_room,
    update_room as svc_update_room,
    delete_room as svc_delete_room,
    bulk_upload_rooms as svc_bulk_upload_rooms,
)
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/rooms", tags=["ROOMS"])


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


# ============================================================================
# 🔹 CREATE - Add a new room to the system
# ============================================================================
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    room_record = await svc_create_room(db, payload)
    # create audit log for room creation
    try:
        new_val = RoomResponse.model_validate(room_record).model_dump()
        entity_id = f"room:{getattr(room_record, 'room_id', None)}"
        changed_by = getattr(locals().get('current_user'), 'user_id', None) or getattr(payload, 'user_id', None)
        await log_audit(entity="room", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
    except Exception:
        pass
    # invalidate rooms cache
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Room created"})


# ============================================================================
# 🔹 READ - Fetch room details (single or list with filters)
# ============================================================================
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
        room_record = await svc_get_room(db, room_id)
        return RoomResponse.model_validate(room_record)

    cache_key = f"rooms:room_type:{room_type_id}:status:{status_filter}:is_freezed:{is_freezed}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    response_list = [Room.model_validate(r) for r in items]
    await set_cached(cache_key, response_list, ttl=120)
    return response_list


# ============================================================================
# 🔹 UPDATE - Modify existing room details
# ============================================================================
@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, payload: RoomUpdate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    room_record = await svc_update_room(db, room_id, payload)
    # audit update
    try:
        new_val = RoomResponse.model_validate(room_record).model_dump()
        entity_id = f"room:{getattr(room_record, 'room_id', None)}"
        changed_by = getattr(locals().get('current_user'), 'user_id', None)
        await log_audit(entity="room", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
    except Exception:
        pass
    # invalidate rooms cache after update
    await invalidate_pattern("rooms:*")
    return RoomResponse.model_validate(room_record).model_copy(update={"message": "Updated successfully"})


# ============================================================================
# 🔹 DELETE - Remove room from system
# ============================================================================
@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    await svc_delete_room(db, room_id)
    # invalidate rooms cache after delete
    await invalidate_pattern("rooms:*")
    return {"message": "Room deleted"}


# ============================================================================
# 🔹 CREATE (BULK) - Upload multiple rooms from Excel file
# ============================================================================
@router.post("/bulk-upload", response_model=BulkRoomUploadResponse, status_code=status.HTTP_200_OK)
async def bulk_upload_rooms(
    file: UploadFile = File(..., description="Excel file with columns: room_no, room_type_id, room_status, freeze_reason"),
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
    _ok: bool = Depends(ensure_not_basic_user),
):
    """
    Bulk upload rooms from an Excel file (only ADMIN/MANAGER allowed).
    
    **Excel File Requirements:**
    - Column 1: `room_no` (required, string) - Room number
    - Column 2: `room_type_id` (required, integer) - ID of the room type
    - Column 3: `room_status` (optional, default: AVAILABLE) - One of: AVAILABLE, BOOKED, MAINTENANCE, FROZEN
    - Column 4: `freeze_reason` (optional, default: NONE) - One of: NONE, CLEANING, ADMIN_LOCK, SYSTEM_HOLD
    
    **Response:**
    - `total_processed`: Total rows in Excel
    - `successfully_created`: Count of rooms created
    - `skipped`: Count of rooms skipped
    - `created_rooms`: List of successfully created rooms with their new IDs
    - `skipped_rooms`: List of skipped rooms with reasons why
    
    **Access Control:** Only non-basic users (admins/managers) can access this endpoint.
    
    **Example curl:**
    ```bash
    curl -X POST http://localhost:8000/api/rooms/bulk-upload \\
      -H "Authorization: Bearer <token>" \\
      -F "file=@rooms.xlsx"
    ```
    """
    # Require WRITE on both Booking and Room_Management
    _require_permissions(user_permissions, [Resources.BOOKING, Resources.ROOM_MANAGEMENT], PermissionTypes.WRITE, require_all=True)
    
    # Read file content
    content = await file.read()
    
    # Call service function to handle bulk upload
    result = await svc_bulk_upload_rooms(db, content)
    
    # Invalidate rooms cache after bulk upload
    await invalidate_pattern("rooms:*")
    
    # Log audit entry for bulk upload operation
    try:
        await log_audit(
            entity="room_bulk_upload",
            entity_id=f"bulk_upload:{result['successfully_created']}_rooms",
            action="INSERT",
            new_value={"total": result["total_processed"], "created": result["successfully_created"], "skipped": result["skipped"]},
            changed_by_user_id=None,
            user_id=None
        )
    except Exception:
        pass
    
    return BulkRoomUploadResponse(**result)
