from fastapi import APIRouter, Depends, status, Query, Security
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundCreate, RefundResponse
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.services.booking_service.bookings_service import create_booking as svc_create_booking, get_booking as svc_get_booking, list_bookings as svc_list_bookings, query_bookings as svc_query_bookings
from app.models.sqlalchemy_schemas.users import Users
from app.dependencies.authentication import get_current_user, check_permission, ensure_only_basic_user
from app.core.exceptions import ForbiddenError
from app.services.refunds_service.refunds_service import cancel_booking_and_create_refund as svc_cancel_booking
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/bookings", tags=["BOOKINGS"])



# ============================================================================
# 🔹 CREATE - Create a new booking
# ============================================================================
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
	payload: BookingCreate,
	db: AsyncSession = Depends(get_db),
	token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
	current_user: Users = Depends(get_current_user),
	_basic_user_check: bool = Depends(ensure_only_basic_user),
):
	"""
	Create a new booking.
	
	Creates a new room booking for the authenticated user. Validates availability for the specified
	check-in and check-out dates and room. Automatically calculates total price based on room rate
	and duration. Only basic users can create bookings for themselves.
	
	**Authorization:** Requires BOOKING:WRITE permission.
	
	Args:
		payload (BookingCreate): Booking request with room_id, check_in, check_out, guest count, etc.
		db (AsyncSession): Database session dependency.
		token_payload (dict): Security token payload validating BOOKING:WRITE permission.
		current_user (Users): Authenticated user making the booking.
		_basic_user_check (bool): Ensure only basic users can create bookings.
	
	Returns:
		BookingResponse: Newly created booking with booking_id, dates, room info, and status.
	
	Raises:
		HTTPException (403): If user lacks BOOKING:WRITE permission.
		HTTPException (400): If room unavailable for specified dates.
		HTTPException (404): If room_id not found.
	
	Side Effects:
		- Invalidates bookings cache pattern ("bookings:*").
		- Creates audit log entry.
		- Reserves room capacity for specified dates.
	"""
	# Pass user_id to service (enforced from authenticated user)
	booking_record = await svc_create_booking(db, payload, user_id=current_user.user_id)
	# create audit log for booking creation
	try:
		new_val = BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})
		entity_id = f"booking:{getattr(booking_record, 'booking_id', None)}"
		changed_by = current_user.user_id
		await log_audit(entity="booking", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
	except Exception:
		# auditing must not break main flow; swallow errors
		pass
	# invalidate bookings cache after new booking
	await invalidate_pattern("bookings:*")
	return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})

# ============================================================================
# 🔹 UPDATE - Cancel a booking and initiate refund
# ============================================================================
@router.post("/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(booking_id: int, payload: RefundCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
	"""
	Cancel a booking and create a refund.
	
	Cancels an existing booking and initiates a refund process. Calculates refund amount based on
	cancellation policy and timing (full refund if within grace period, partial otherwise). Booking
	status changes to CANCELLED and room availability is restored. Refund is created in PENDING status.
	
	Args:
		booking_id (int): The ID of the booking to cancel.
		payload (RefundCreate): Refund request with reason and other details.
		db (AsyncSession): Database session dependency.
		current_user (Users): Authenticated user initiating cancellation.
	
	Returns:
		RefundResponse: Created refund record with refund_id, amount, and status.
	
	Raises:
		HTTPException (404): If booking_id not found or not owned by user.
		HTTPException (400): If booking cannot be cancelled (already cancelled, check-in passed, etc.).
	
	Side Effects:
		- Changes booking status to CANCELLED.
		- Creates refund record in PENDING status.
		- Restores room availability.
		- Creates audit log entry for booking cancellation.
	"""
	refund_record = await svc_cancel_booking(db, booking_id, payload, current_user)
	try:
		new_val = RefundResponse.model_validate(refund_record).model_dump()
		entity_id = f"booking:{booking_id}"
		changed_by = getattr(locals().get('current_user'), 'user_id', None)
		await log_audit(entity="booking", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
	except Exception:
		pass
	return RefundResponse.model_validate(refund_record)


# ============================================================================
# 🔹 READ - Fetch booking details (single or list with filters)
# ============================================================================
@router.get("/", response_model=List[BookingResponse])
async def get_bookings(
    booking_id: Optional[int] = None,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ"]),
    current_user: Users = Depends(get_current_user),
):
    """
    Retrieve bookings (single, list, or filtered).
    
    Flexible GET endpoint supporting multiple query modes:
    - **Basic users (role_id=1):** Can only view their own bookings (optionally filter by status).
    - **Privileged users (BOOKING:READ):** Can view all bookings system-wide (with optional status filter).
    
    Respects pagination with limit and offset. Supports optional status filtering for both roles.
    Basic users cannot access bookings they don't own; attempting so returns 403.
    
    Args:
        booking_id (Optional[int]): Query parameter - if provided, return single booking.
        status (Optional[str]): Query parameter - filter by booking status (CONFIRMED, CANCELLED, etc).
        limit (int): Pagination limit (default 20, max 200).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        token_payload (dict): Security token payload validating BOOKING:READ permission.
        current_user (Users): Authenticated user.
    
    Returns:
        List[BookingResponse]: List of bookings matching criteria (basic users get only their own).
    
    Raises:
        HTTPException (403): If user lacks BOOKING:READ and tries to access other user's booking.
        HTTPException (404): If booking_id not found.
    """

    is_basic_user = getattr(current_user, "role_id", None) == 1
    has_booking_read = True  # User has BOOKING:READ via Security

    # BASIC USER LOGIC
    if is_basic_user:
        if booking_id:
            booking_record = await svc_get_booking(db, booking_id)
            if booking_record.user_id != current_user.user_id:
                raise ForbiddenError("Insufficient privileges to access this booking")
            return [BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})]

        # All their own bookings (optional status filter)
        items = await svc_query_bookings(db, user_id=current_user.user_id, status=status)
        return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]

    # PRIVILEGED USER LOGIC
    if not has_booking_read:
        raise ForbiddenError("Insufficient permissions to access bookings")

    if booking_id:
        booking_record = await svc_get_booking(db, booking_id)
        return [BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})]

    # List all bookings (filtered or paginated)
    if status:
        items = await svc_query_bookings(db, user_id=None, status=status)
    else:
        items = await svc_list_bookings(db, limit=limit, offset=offset)

    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]
