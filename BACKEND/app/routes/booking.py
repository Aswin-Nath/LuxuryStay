from typing import List, Optional
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    Security,
    status,
    Query,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ==========================================================
# 🧩 Core Imports
# ==========================================================
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.dependencies.authentication import get_current_user, check_permission
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit

# ==========================================================
# 🧱 Schemas
# ==========================================================
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.schemas.pydantic_models.refunds import RefundResponse
# ==========================================================
# ⚙️ Services
# ==========================================================
from app.services.bookings_service import (
    get_booking as svc_get_booking,
    list_bookings as svc_list_bookings,
    query_bookings as svc_query_bookings,
)
from app.services.refunds_service import (
    cancel_booking_and_create_refund as svc_cancel_booking,
)


# ==========================================================
# 📦 Router Definition
# ==========================================================
router = APIRouter(prefix="/bookings", tags=["BOOKINGS"])




# ==========================================================
# 🔹 UPDATE - Cancel booking & create refund
# ==========================================================
@router.post("/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    refund_record = await svc_cancel_booking(db, booking_id, current_user)

    try:
        new_val = RefundResponse.model_validate(refund_record).model_dump()
        entity_id = f"booking:{booking_id}"
        await log_audit(entity="booking", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass

    await invalidate_pattern("bookings:*")
    await invalidate_pattern("refunds:*")
    return RefundResponse.model_validate(refund_record)


# ==========================================================
# 🔹 READ - Customer: Get own booking by ID
# ==========================================================
@router.get("/customer/{booking_id}", response_model=BookingResponse)
async def get_customer_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    booking_record = await svc_get_booking(db, booking_id)
    if booking_record.user_id != current_user.user_id:
        raise ForbiddenException("You don't have permission to access this booking")

    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ==========================================================
# 🔹 READ - Admin: Get booking by ID
# ==========================================================
@router.get("/admin/{booking_id}", response_model=BookingResponse)
async def get_admin_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    booking_record = await svc_get_booking(db, booking_id)
    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ==========================================================
# 🔹 READ - Customer: List own bookings
# ==========================================================
@router.get("/customer", response_model=List[BookingResponse])
async def get_customer_bookings(
    status: Optional[str] = Query(None, description="Filter by booking status (CONFIRMED, PENDING, CANCELLED, CHECKED_IN, CHECKED_OUT)"),
    min_price: Optional[float] = Query(None, description="Filter bookings with total_price >= min_price"),
    max_price: Optional[float] = Query(None, description="Filter bookings with total_price <= max_price"),
    room_type_id: Optional[int] = Query(None, description="Comma-separated room type IDs to filter by (e.g., 1,2,3)"),
    check_in_date: Optional[str] = Query(None, description="Filter bookings with check_in >= this date (YYYY-MM-DD format)"),
    check_out_date: Optional[str] = Query(None, description="Filter bookings with check_out <= this date (YYYY-MM-DD format)"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Retrieve current user's bookings with advanced filtering.
    
    Supports filtering by status, price range, room types, and date range.
    
    Query Parameters:
        - status: Filter by booking status (CONFIRMED, PENDING, CANCELLED, CHECKED_IN, CHECKED_OUT)
        - min_price/max_price: Filter by total price range
        - room_type_id: Comma-separated room type IDs (e.g., "1,2,3")
        - check_in_date: Filter bookings from this date (YYYY-MM-DD)
        - check_out_date: Filter bookings until this date (YYYY-MM-DD)
        - limit/offset: Pagination parameters
    
    Examples:
        GET /bookings/customer?status=CONFIRMED&min_price=100&max_price=500
        GET /bookings/customer?room_type_id=1,2&check_in_date=2025-12-01
    """

    # Parse dates
    check_in_date_parsed = None
    check_out_date_parsed = None
    if check_in_date:
        try:
            check_in_date_parsed = datetime.strptime(check_in_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="check_in_date must be in YYYY-MM-DD format"
            )
    
    if check_out_date:
        try:
            check_out_date_parsed = datetime.strptime(check_out_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="check_out_date must be in YYYY-MM-DD format"
            )
    
    # Convert price filters to Decimal
    from decimal import Decimal
    min_price_decimal = Decimal(str(min_price)) if min_price is not None else None
    max_price_decimal = Decimal(str(max_price)) if max_price is not None else None
    
    # Query with filters
    items = await svc_query_bookings(
        db, 
        user_id=current_user.user_id, 
        status=status,
        min_price=min_price_decimal,
        max_price=max_price_decimal,
        room_type_id=room_type_id,
        check_in_date=check_in_date_parsed,
        check_out_date=check_out_date_parsed,
        limit=limit,
        offset=offset,
    )
    
    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


# ==========================================================
# 🔹 READ - Admin: List all bookings (filterable)
# ==========================================================
@router.get("/admin", response_model=List[BookingResponse])
async def get_admin_bookings(
    min_price:Optional[int]=Query(None),
    max_price:Optional[int]=Query(None),
    room_type_id:Optional[int]=Query(None),
    check_in_date:Optional[str]=Query(None),
    check_out_date:Optional[str]=Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    items = await svc_query_bookings(
        db,
        room_type_id=room_type_id,
        status=status,
        min_price=min_price,
        max_price=max_price,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        limit=limit,
        offset=offset,
    )
    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


# ==========================================================
# 🔹 READ - Get all distinct booking statuses
# ==========================================================
@router.get("/statuses", response_model=List[str])
async def get_booking_statuses(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ"]),
):
    """
    Retrieve all distinct booking statuses from the database.
    
    Used for populating status filter dropdowns in the UI.
    Returns unique statuses that have been used in bookings.
    
    Returns:
        List[str]: List of unique booking status values
    
    Examples:
        GET /bookings/statuses → ["CONFIRMED", "PENDING", "CANCELLED", "CHECKED_IN", "CHECKED_OUT"]
    """
    from sqlalchemy import select, distinct
    
    stmt = select(distinct(Bookings.status)).order_by(Bookings.status)
    result = await db.execute(stmt)
    statuses = [row[0] for row in result.fetchall() if row[0]]
    
    return statuses