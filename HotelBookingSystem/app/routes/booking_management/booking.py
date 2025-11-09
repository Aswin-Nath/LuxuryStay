from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundCreate, RefundResponse
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.services.booking_service.bookings_service import create_booking as svc_create_booking, get_booking as svc_get_booking, list_bookings as svc_list_bookings, query_bookings as svc_query_bookings
from app.models.sqlalchemy_schemas.users import Users
from app.dependencies.authentication import get_current_user, get_user_permissions, ensure_only_basic_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.refunds_service.refunds_service import cancel_booking_and_create_refund as svc_cancel_booking
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/bookings", tags=["BOOKINGS"])



@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
	payload: BookingCreate,
	db: AsyncSession = Depends(get_db),
	user_permissions: dict = Depends(get_user_permissions),
	current_user: Users = Depends(get_current_user),
	_basic_user_check: bool = Depends(ensure_only_basic_user),
):
	# Permission check: require BOOKING.WRITE
	if not (
		Resources.BOOKING.value in user_permissions
		and PermissionTypes.WRITE.value in user_permissions[Resources.BOOKING.value]
	):
		raise ForbiddenError("Insufficient permissions to create bookings")

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

@router.post("/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(booking_id: int, payload: RefundCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
	refund_record = await svc_cancel_booking(db, booking_id, payload, current_user)
	# audit booking cancellation (status change)
	try:
		new_val = RefundResponse.model_validate(refund_record).model_dump()
		entity_id = f"booking:{booking_id}"
		changed_by = getattr(locals().get('current_user'), 'user_id', None)
		await log_audit(entity="booking", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=changed_by, user_id=changed_by)
	except Exception:
		pass
	return RefundResponse.model_validate(refund_record)


@router.get("/", response_model=List[BookingResponse])
async def get_bookings(
    booking_id: Optional[int] = None,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
    current_user: Users = Depends(get_current_user),
):
    """
    Unified GET for bookings (simplified).

    - Basic user (role_id == 1):
        • If booking_id → return that booking (must own it)
        • Else → return all their own bookings (filter by status if given)
    - Privileged user (has booking WRITE permission):
        • If booking_id → return that booking
        • Else → return all bookings (filter by status if given, else paginated)
    - Others → 403
    """

    is_basic_user = getattr(current_user, "role_id", None) == 1
    has_booking_write = (
        Resources.BOOKING.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.BOOKING.value]
    )

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
    if not has_booking_write:
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
