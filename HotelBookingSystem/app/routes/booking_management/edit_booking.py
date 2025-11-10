from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.schemas.pydantic_models.booking_edits import BookingEditCreate, BookingEditResponse,ReviewPayload,DecisionPayload
from app.services.booking_service.booking_edit import (
    create_booking_edit_service,
    get_all_booking_edits_service,
    review_booking_edit_service,
    decision_on_booking_edit_service,
    change_room_status,
)
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/booking-edits", tags=["BOOKING-EDITS"])


# ============================================================================
# 🔹 CREATE - Submit a booking edit request
# ============================================================================
@router.post("/", response_model=BookingEditResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_edit(
    payload: BookingEditCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a booking edit request (customer-initiated).
    
    Allows customers to request changes to their existing bookings (room change, date change, etc).
    Creates an edit request in PENDING status awaiting admin review. Only one active edit per booking
    allowed at a time. Prevents duplicate requests within a short time window.
    
    Args:
        payload (BookingEditCreate): Edit request with booking_id, new room/dates, reason, etc.
        db (AsyncSession): Database session dependency.
        current_user: Authenticated user creating the edit request.
    
    Returns:
        BookingEditResponse: Created edit request with edit_id, status PENDING, timestamps.
    
    Raises:
        HTTPException (404): If booking_id not found or not owned by user.
        HTTPException (409): If active edit already exists for the booking.
    
    Side Effects:
        - Creates booking edit record in PENDING status.
        - Creates audit log entry.
    """
    booking_edit_record = await create_booking_edit_service(payload, db, current_user)
    # audit booking edit create
    try:
        new_val = BookingEditResponse.model_validate(booking_edit_record).model_dump()
        entity_id = f"booking_edit:{getattr(booking_edit_record, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return booking_edit_record


# ============================================================================
# 🔹 READ - Fetch booking edit requests for a booking
# ============================================================================
@router.get("/{booking_id}", response_model=BookingEditResponse | list[BookingEditResponse])
async def get_booking_edits(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Retrieve all booking edit requests for a specific booking.
    
    Fetches all edit requests (history) for a booking. Authorization varies by user role:
    - **Basic users:** Can only access edit requests for bookings they own.
    - **Non-basic users:** Must have REFUND_APPROVAL:WRITE permission to access other users' edits.
    
    Args:
        booking_id (int): The booking ID to fetch edits for.
        db (AsyncSession): Database session dependency.
        current_user: Authenticated user.
        user_permissions (dict): Current user's permissions.
    
    Returns:
        BookingEditResponse | list[BookingEditResponse]: Single edit or list of all edit requests.
    
    Raises:
        HTTPException (403): If user lacks permission to access this booking's edits.
        HTTPException (404): If booking_id not found.
    """
    # Authorization
    is_basic_user = getattr(current_user, "role_id", None) == 1
    if is_basic_user:
        # verify ownership by loading booking

        query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
        booking = query_result.scalars().first()
        if not booking or booking.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to access this booking's edits")
    else:
        # require BOOKING.WRITE permission for non-basic users
        if not (Resources.REFUND_APPROVAL.value in user_permissions and PermissionTypes.WRITE.value in user_permissions.get(Resources.REFUND_APPROVAL.value, set())):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required to access booking edits")

    return await get_all_booking_edits_service(booking_id, db)



# ============================================================================
# 🔹 UPDATE - Lock or unlock a room status
# ============================================================================
@router.post("/rooms/{room_id}/status")
async def change_room_status_route(
    room_id: int,
    lock: bool = Query(True, description="true to lock the room, false to unlock"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Lock or unlock a room status.
    
    Admin-only endpoint to lock or unlock room availability. Locked rooms cannot be booked or
    edited during the lock period. Used during maintenance, overbooking disputes, or edit review.
    
    **Authorization:** Requires ROOM_MANAGEMENT:WRITE permission.
    
    Args:
        room_id (int): The room ID to lock/unlock.
        lock (bool): True to lock, False to unlock the room.
        db (AsyncSession): Database session dependency.
        current_user: Authenticated user (admin).
        user_permissions (dict): Current user's permissions.
    
    Returns:
        dict: Confirmation with room_id, room_status, and freeze_reason.
    
    Raises:
        HTTPException (403): If user lacks ROOM_MANAGEMENT:WRITE permission.
        HTTPException (404): If room_id not found.
    """
    # Permission check: only admins/managers with ROOM_MANAGEMENT.WRITE can perform this
    if not user_permissions or (
        Resources.ROOM_MANAGEMENT.value not in user_permissions
        or PermissionTypes.WRITE.value not in user_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    room = await change_room_status(db, room_id, lock)
    # Normalize enum values to strings for JSON response
    r_status = getattr(room, 'room_status', None)
    fr = getattr(room, 'freeze_reason', None)
    return {
        "ok": True,
        "room_id": room_id,
        "room_status": str(r_status),
        "freeze_reason": str(fr)
    }



# ============================================================================
# 🔹 UPDATE - Admin review and suggest new rooms for booking edit
# ============================================================================
@router.post("/{edit_id}/review")
async def review_booking_edit(
    edit_id: int,
    payload: ReviewPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Admin review and suggest room changes for a booking edit request.
    
    Admin examines a pending edit request and suggests alternative rooms for the customer.
    Locks the suggested rooms for 30 minutes to prevent overbooking. Admin can provide multiple
    room options or reject the request. Rooms remain locked pending customer decision.
    
    **Authorization:** Requires ROOM_MANAGEMENT:WRITE permission.
    
    Args:
        edit_id (int): The booking edit request ID to review.
        payload (ReviewPayload): Admin's decision with suggested rooms and notes.
        db (AsyncSession): Database session dependency.
        current_user: Authenticated admin user.
        user_permissions (dict): Admin's permissions.
    
    Returns:
        BookingEditResponse: Updated edit request with status UNDER_REVIEW and suggested rooms.
    
    Raises:
        HTTPException (403): If user lacks ROOM_MANAGEMENT:WRITE permission.
        HTTPException (404): If edit_id not found.
    
    Side Effects:
        - Locks suggested rooms for 30 minutes.
        - Changes edit status to UNDER_REVIEW.
        - Creates audit log entry.
    """
    # Check admin access against canonical permission enums
    if not user_permissions or (
        Resources.ROOM_MANAGEMENT.value not in user_permissions
        or PermissionTypes.WRITE.value not in user_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    booking_edit_record = await review_booking_edit_service(edit_id, payload, db, current_user)
    # audit admin review action
    try:
        new_val = BookingEditResponse.model_validate(booking_edit_record).model_dump()
        entity_id = f"booking_edit:{getattr(booking_edit_record, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return booking_edit_record


# ============================================================================
# 🔹 UPDATE - Customer accept/reject proposed booking edit
# ============================================================================
@router.post("/{edit_id}/decision")
async def decision_booking_edit(
    edit_id: int,
    payload: DecisionPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Customer accept or reject admin-proposed booking edit.
    
    Customer reviews admin's suggested rooms/changes and accepts or rejects. Accepting
    finalizes the booking change and applies new dates/room. Rejecting returns edit to
    PENDING status and unlocks suggested rooms. 30-minute lock expires if customer
    doesn't respond in time.
    
    Args:
        edit_id (int): The booking edit request ID to decide on.
        payload (DecisionPayload): Customer's decision (ACCEPTED or REJECTED).
        db (AsyncSession): Database session dependency.
        current_user: Authenticated user (booking owner).
    
    Returns:
        BookingEditResponse: Updated edit request with final status and decision timestamp.
    
    Raises:
        HTTPException (404): If edit_id not found or not owned by user.
        HTTPException (400): If edit not in UNDER_REVIEW status or lock expired.
    
    Side Effects:
        - Finalizes or rejects booking changes.
        - Unlocks rooms from admin's lock.
        - Updates booking if accepted.
        - Creates audit log entry.
    """
    booking_edit_record = await decision_on_booking_edit_service(edit_id, payload, db, current_user)
    # audit customer decision
    try:
        new_val = BookingEditResponse.model_validate(booking_edit_record).model_dump()
        entity_id = f"booking_edit:{getattr(booking_edit_record, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return booking_edit_record