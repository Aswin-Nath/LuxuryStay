from fastapi import APIRouter, Depends, Security, status, Query, UploadFile, File
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import (
    RoomCreate, RoomResponse, Room, RoomUpdate, BulkRoomUploadResponse
)
from app.dependencies.authentication import check_permission, get_current_user, ensure_not_basic_user
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


# ============================================================================
# 🔹 CREATE - Add a new room to the system
# ============================================================================
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """
    Create a new room in the system.
    
    Creates a new room with the provided details. The room number must be unique.
    Requires WRITE permission on both BOOKING and ROOM_MANAGEMENT resources.
    
    **Request Body:**
    - `room_no` (str): Unique room number (e.g., "101", "102")
    - `room_type_id` (int): ID of the room type (must exist)
    
    **Response:**
    - Returns the newly created room with all details including room_id, status, price, etc.
    - Includes an audit log entry for the creation.
    
    **Access Control:** Requires WRITE permission on BOOKING and ROOM_MANAGEMENT resources.
    
    Args:
        payload (RoomCreate): Pydantic model containing room creation data.
        db (AsyncSession): Database session dependency.
        user_permissions (dict): User's permission dictionary from authentication.
    
    Returns:
        RoomResponse: The newly created room object with success message.
    
    Raises:
        ForbiddenError: If user lacks required permissions.
        HTTPException (409): If room number already exists.
        HTTPException (404): If room type not found.
    """
    room_record = await svc_create_room(db, payload)
    # create audit log for room creation
    try:
        new_val = RoomResponse.model_validate(room_record).model_dump()
        entity_id = f"room:{getattr(room_record, 'room_id', None)}"
        await log_audit(entity="room", entity_id=entity_id, action="INSERT", new_value=new_val)
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
    """
    Fetch room(s) with optional filters and caching.
    
    **Dual Behavior:**
    - If `room_id` query param is provided: Returns a single room as RoomResponse.
    - Otherwise: Returns a list of rooms matching optional filters (room_type_id, status_filter, is_freezed).
    
    **Query Parameters:**
    - `room_id` (int, optional): Return single room by ID.
    - `room_type_id` (int, optional): Filter by room type.
    - `status_filter` (str, optional): Filter by status (AVAILABLE, BOOKED, MAINTENANCE, FROZEN).
    - `is_freezed` (bool, optional): True for frozen rooms, False for non-frozen.
    
    **Caching:** List results are cached for 120 seconds to improve performance.
    
    **Access Control:** Only non-basic users (admins/managers) may access this endpoint.
    
    Args:
        room_id (Optional[int]): Single room ID if fetching one room.
        room_type_id (Optional[int]): Filter by room type.
        status_filter (Optional[str]): Filter by room status.
        is_freezed (Optional[bool]): Filter by freeze status.
        db (AsyncSession): Database session dependency.
        _current_user: Authenticated user (dependency).
        _ok (bool): Authorization check (dependency).
    
    Returns:
        Union[RoomResponse, List[Room]]: Single room or list of rooms depending on room_id parameter.
    
    Raises:
        HTTPException (404): If room_id is provided but room not found.
        ForbiddenError: If user is a basic user.
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
async def update_room(room_id: int, payload: RoomUpdate, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "ROOM_MANAGEMENT:WRITE"])):
    """
    Update an existing room's information.
    
    Updates specified fields of a room. Only provided fields are updated (partial updates supported).
    Requires WRITE permission on both BOOKING and ROOM_MANAGEMENT resources.
    
    **Path Parameters:**
    - `room_id` (int): The ID of the room to update.
    
    **Request Body:**
    - Pydantic model with fields to update (all optional).
    
    **Response:**
    - Returns the updated room object with all current details.
    - Includes an audit log entry for the update.
    
    **Access Control:** Requires WRITE permission on BOOKING and ROOM_MANAGEMENT resources.
    
    Args:
        room_id (int): The room ID to update.
        payload (RoomUpdate): Pydantic model with fields to update.
        db (AsyncSession): Database session dependency.
        user_permissions (dict): User's permission dictionary.
    
    Returns:
        RoomResponse: The updated room object with success message.
    
    Raises:
        ForbiddenError: If user lacks required permissions.
        HTTPException (404): If room not found.
        HTTPException (409): If new room number conflicts with another room.
    """
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
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "ROOM_MANAGEMENT:WRITE"])):
    """
    Soft-delete a room from the system.
    
    Marks the room as deleted (soft delete). The room record remains in the database for historical purposes
    but is excluded from normal queries. Requires WRITE permission on both BOOKING and ROOM_MANAGEMENT resources.
    
    **Path Parameters:**
    - `room_id` (int): The ID of the room to delete.
    
    **Response:**
    - Returns a success message.
    - Clears all room-related cache entries.
    
    **Access Control:** Requires WRITE permission on BOOKING and ROOM_MANAGEMENT resources.
    
    Args:
        room_id (int): The room ID to delete.
        db (AsyncSession): Database session dependency.
        user_permissions (dict): User's permission dictionary.
    
    Returns:
        dict: Dictionary with "message" key confirming deletion.
    
    Raises:
        ForbiddenError: If user lacks required permissions.
        HTTPException (404): If room not found.
    """
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
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "ROOM_MANAGEMENT:WRITE"]),
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
