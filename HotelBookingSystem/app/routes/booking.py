from fastapi import APIRouter, Depends, status, Query, Security
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundCreate, RefundResponse
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.services.bookings_service import create_booking as svc_create_booking, get_booking as svc_get_booking, list_bookings as svc_list_bookings, query_bookings as svc_query_bookings
from app.models.sqlalchemy_schemas.users import Users
from app.dependencies.authentication import get_current_user, check_permission
from app.core.exceptions import ForbiddenException
from app.services.refunds_service import cancel_booking_and_create_refund as svc_cancel_booking
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_util import log_audit


router = APIRouter(prefix="/bookings", tags=["BOOKINGS"])



# ============================================================================
# 🔹 CREATE - Create a new booking
# ============================================================================
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
	payload: BookingCreate,
	db: AsyncSession = Depends(get_db),
	token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
	current_user: Users = Depends(get_current_user),
):
	"""
	Create a new booking.
	
	Creates a new room booking for the authenticated user. Validates availability for the specified
	check-in and check-out dates and room. Automatically calculates total price based on room rate
	and duration. Only CUSTOMER role users can create bookings for themselves.
	
	**Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
	
	Args:
		payload (BookingCreate): Booking request with room_id, check_in, check_out, guest count, etc.
		db (AsyncSession): Database session dependency.
		token_payload (dict): Security token payload validating BOOKING:WRITE permission and CUSTOMER role.
		current_user (Users): Authenticated user making the booking (CUSTOMER role).
	
	Returns:
		BookingResponse: Newly created booking with booking_id, dates, room info, and status.
	
	Raises:
		HTTPException (401): If token invalid or blacklisted.
		HTTPException (403): If lacks BOOKING:WRITE permission or not CUSTOMER role.
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
async def cancel_booking(booking_id: int, payload: RefundCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),):
	"""
	Cancel a booking and create a refund.
	
	Cancels an existing booking and initiates a refund process. Calculates refund amount based on
	cancellation policy and timing (full refund if within grace period, partial otherwise). Booking
	status changes to CANCELLED and room availability is restored. Refund is created in PENDING status.
	
	**Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
	
	Args:
		booking_id (int): The ID of the booking to cancel.
		payload (RefundCreate): Refund request with reason and other details.
		db (AsyncSession): Database session dependency.
		current_user (Users): Authenticated CUSTOMER role user initiating cancellation.
		token_payload (dict): Security token validating BOOKING:WRITE permission and CUSTOMER role.
	
	Returns:
		RefundResponse: Created refund record with refund_id, amount, and status.
	
	Raises:
		HTTPException (401): If token invalid or blacklisted.
		HTTPException (403): If lacks BOOKING:WRITE permission or not CUSTOMER role.
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
	# invalidate bookings and refunds cache after cancellation
	await invalidate_pattern("bookings:*")
	await invalidate_pattern("refunds:*")
	return RefundResponse.model_validate(refund_record)


# ============================================================================
# 🔹 READ - Customer endpoint to fetch specific own booking by ID
# ============================================================================
@router.get("/customer/{booking_id}", response_model=BookingResponse)
async def get_customer_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"])
):
    """
    Retrieve a specific booking belonging to current user only.
    
    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role.
    Users can only see their own bookings.
    
    Args:
        booking_id (int): ID of the booking to retrieve.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user with CUSTOMER role.
        token_payload (dict): Security token validating BOOKING:READ permission and CUSTOMER role.
    
    Returns:
        BookingResponse: The requested booking if owned by current user.
    
    Raises:
        HTTPException (401): If token invalid or blacklisted.
        HTTPException (403): If lacks BOOKING:READ permission or not CUSTOMER role.
        HTTPException (404): If booking not found.
    """
    booking_record = await svc_get_booking(db, booking_id)
    if booking_record.user_id != current_user.user_id:
        raise ForbiddenException("You don't have permission to access this booking")
    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 READ - Admin endpoint to fetch any booking by ID
# ============================================================================
@router.get("/admin/{booking_id}", response_model=BookingResponse)
async def get_admin_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    """
    Retrieve a specific booking by its ID. Admin-only endpoint.
    
    **Authorization:** Requires BOOKING:READ permission AND ADMIN role.
    
    Admin users (super_admin, normal_admin, content_admin, BACKUP_ADMIN) can access any booking 
    and view detailed information.
    
    Args:
        booking_id (int): ID of the booking to retrieve.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user with ADMIN role.
        token_payload (dict): Security token with BOOKING:READ permission and ADMIN role.
    
    Returns:
        BookingResponse: The requested booking record.
    
    Raises:
        HTTPException (401): If token invalid or blacklisted.
        HTTPException (403): If lacks BOOKING:READ permission or not ADMIN role.
        HTTPException (404): If booking not found.
    """
    booking_record = await svc_get_booking(db, booking_id)
    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 READ - Customer endpoint to fetch own bookings (list)
# ============================================================================
@router.get("/customer", response_model=List[BookingResponse])
async def get_customer_bookings(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"])

):
    """
    Retrieve current user's own bookings only (list).
    
    **Authorization:** No special scope required. Users can only see their own bookings.
    
    Use GET /customer/{booking_id} to fetch a specific booking.
    
    Args:
        status (Optional[str]): Filter by booking status (CONFIRMED, CANCELLED, etc).
        limit (int): Pagination limit (default 20, max 200).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        List[BookingResponse]: List of current user's bookings matching criteria.
    
    Raises:
        None - Always returns user's own bookings or empty list.
    """
    # Get all own bookings (optionally filtered by status)
    items = await svc_query_bookings(db, user_id=current_user.user_id, status=status)
    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


# ============================================================================
# 🔹 READ - Admin endpoint to fetch all bookings with advanced filtering (list)
# ============================================================================
@router.get("/admin", response_model=List[BookingResponse])
async def get_admin_bookings(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    """
    Retrieve all bookings with advanced filtering (list). Admin-only endpoint.
    
    **Authorization:** Requires BOOKING:READ permission AND ADMIN role.
    
    Admin users (super_admin, normal_admin, content_admin, BACKUP_ADMIN) can query all bookings 
    system-wide with optional status filtering.
    
    Use GET /admin/{booking_id} to fetch a specific booking.
    
    Args:
        status (Optional[str]): Filter by booking status (CONFIRMED, CANCELLED, etc).
        limit (int): Pagination limit (default 20, max 200).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user with ADMIN role.
        token_payload (dict): Security token with BOOKING:READ permission and ADMIN role.
    
    Returns:
        List[BookingResponse]: List of all bookings matching criteria.
    
    Raises:
        HTTPException (401): If token invalid or blacklisted.
        HTTPException (403): If lacks BOOKING:READ permission or not ADMIN role.
    """
    # List all bookings (filtered by status or paginated)
    if status:
        items = await svc_query_bookings(db, user_id=None, status=status)
    else:
        items = await svc_list_bookings(db, limit=limit, offset=offset)
    
    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]
