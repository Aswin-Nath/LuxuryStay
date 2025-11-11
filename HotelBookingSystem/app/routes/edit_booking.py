from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user, check_permission
from app.schemas.pydantic_models.booking_edits import BookingEditCreate, BookingEditResponse, ReviewPayload, DecisionPayload, UpdateRoomOccupancyRequest
from app.services.booking_edit import (
    create_booking_edit_service,
    get_all_booking_edits_service,
    review_booking_edit_service,
    decision_on_booking_edit_service,
    change_room_status,
    update_room_occupancy_service,
)
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.utils.audit_util import log_audit

router = APIRouter(prefix="/booking-edits", tags=["BOOKING-EDITS"])


# ============================================================================
# 🔹 CREATE - Submit a booking edit request
# ============================================================================
@router.post("/", response_model=BookingEditResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_edit(
    payload: BookingEditCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
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
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
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
        token_payload (dict): Security token payload validating REFUND_APPROVAL:WRITE permission.
    
    Returns:
        BookingEditResponse | list[BookingEditResponse]: Single edit or list of all edit requests.
    
    Raises:
        HTTPException (403): If user lacks permission to access this booking's edits.
        HTTPException (404): If booking_id not found.
    """

    query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    booking = query_result.scalars().first()
    if not booking or booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to access this booking's edits")

    return await get_all_booking_edits_service(booking_id, db)




# ============================================================================
# 🔹 UPDATE - Admin review and suggest new rooms for booking edit
# ============================================================================
@router.post("/{edit_id}/review")















async def review_booking_edit(
    edit_id: int,
    payload: ReviewPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
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
        token_payload (dict): Security token payload validating ROOM_MANAGEMENT:WRITE permission.
    
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


# ============================================================================
# 🔹 UPDATE - Customer update room occupancy (adults/children) directly
# ============================================================================
@router.patch("/{booking_id}/occupancy", status_code=status.HTTP_200_OK)
async def update_occupancy(
    booking_id: int,
    payload: UpdateRoomOccupancyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Customer update room occupancy (adults and children count) for their booking.
    
    Allows customers to update the number of adults and children in each room of their booking
    without requiring admin approval. This is a direct update to the booking_room_map table.
    
    Only the booking owner (customer) can update occupancy for their bookings.
    Each room must maintain at least 1 adult - validation enforces this requirement.
    
    **Authorization:** Only the booking owner (customer who made the booking) can update occupancy.
    
    **Request Format:**
    ```json
    {
      "room_updates": [
        {
          "room_id": 101,
          "adults": 2,
          "children": 1
        },
        {
          "room_id": 102,
          "adults": 1,
          "children": 0
        }
      ]
    }
    ```
    
    Args:
        booking_id (int): The booking ID to update occupancy for.
        room_occupancy_updates (dict): Dictionary with "room_updates" key containing list of room occupancy updates.
        db (AsyncSession): Database session dependency.
        current_user: Authenticated user (must be booking owner).
    
    Returns:
        dict: Updated booking rooms with new occupancy details.
    
    Raises:
        HTTPException (403): If user is not the booking owner.
        HTTPException (404): If booking_id not found.
        HTTPException (404): If room_id not in the booking.
        HTTPException (400): If room has 0 adults (violates minimum 1 adult requirement).
        HTTPException (400): If adults or children values are negative.
    
    Side Effects:
        - Updates booking_room_map table with new occupancy values.
        - Creates audit log entry for each room updated.
        - No admin approval needed.
    
    Example:
        >>> # Update occupancy for booking 1001
        >>> # Room 101: 2 adults, 1 child
        >>> # Room 102: 1 adult, 0 children
        >>> response = await client.patch(
        ...     "/booking-edits/1001/occupancy",
        ...     json={
        ...         "room_updates": [
        ...             {"room_id": 101, "adults": 2, "children": 1},
        ...             {"room_id": 102, "adults": 1, "children": 0}
        ...         ]
        ...     }
        ... )
        >>> # Returns: {
        >>> #     "booking_id": 1001,
        >>> #     "rooms": [
        >>> #         {"room_id": 101, "adults": 2, "children": 1, ...},
        >>> #         {"room_id": 102, "adults": 1, "children": 0, ...}
        >>> #     ]
        >>> # }
    """
    updated_rooms = await update_room_occupancy_service(
        booking_id=booking_id,
        room_occupancy_updates=payload.model_dump(),
        db=db,
        current_user=current_user
    )
    
    # audit occupancy update
    try:
        entity_id = f"booking_room_maps:{booking_id}"
        new_val = {
            "booking_id": booking_id,
            "rooms": [
                {
                    "room_id": room.room_id,
                    "room_type_id": room.room_type_id,
                    "adults": room.adults,
                    "children": room.children
                }
                for room in updated_rooms
            ]
        }
        await log_audit(
            entity="booking_occupancy",
            entity_id=entity_id,
            action="UPDATE",
            new_value=new_val,
            changed_by_user_id=getattr(current_user, 'user_id', None),
            user_id=getattr(current_user, 'user_id', None)
        )
    except Exception:
        pass
    
    return {
        "booking_id": booking_id,
        "rooms": [
            {
                "room_id": room.room_id,
                "room_type_id": room.room_type_id,
                "adults": room.adults,
                "children": room.children,
                "is_room_active": room.is_room_active
            }
            for room in updated_rooms
        ]
    }