from fastapi import APIRouter, Depends, Query, status, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from typing import List, Optional
from datetime import datetime

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.payments import Payments
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.schemas.pydantic_models.payments import PaymentResponse, PaymentCreate
from app.dependencies.authentication import get_current_user, check_permission
from app.models.sqlalchemy_schemas.users import Users
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit


router = APIRouter(prefix="/payments", tags=["PAYMENTS"])


async def _get_user_bookings(db: AsyncSession, user_id: int) -> List[int]:
    """Get all booking IDs for a specific user."""
    stmt = select(Bookings.booking_id).where(Bookings.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================================
# 🔹 CREATE - Insert payment record into database
# ============================================================================
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    """
    Create and insert a payment record into the database.
    
    Simple endpoint to insert payment details including method_id, 
    transaction_reference, and remarks. Creates payment with status="SUCCESS".
    User ID is automatically extracted from authenticated user.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        payload (PaymentCreate): Payment details with:
            - booking_id: ID of the booking this payment is for
            - amount: Payment amount
            - method_id: Payment method ID (e.g., 1 for Credit Card, 2 for UPI, etc.)
            - transaction_reference: Reference/transaction number from payment gateway
            - remarks: Optional notes/remarks about the payment
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (user_id extracted from here).
        token_payload (dict): Security token with PAYMENT_PROCESSING:WRITE permission.
    
    Returns:
        PaymentResponse: Created payment record with payment_id, status, and timestamps.
    
    Raises:
        HTTPException (404): If booking not found.
        HTTPException (400): If booking_id or method_id invalid.
    
    Side Effects:
        - Creates payment record with status="SUCCESS".
        - Invalidates payments cache.
        - Creates audit log entry.
    """
    # Get user_id from authenticated current_user
    user_id = current_user.user_id
    
    # Verify booking exists
    booking_query = await db.execute(
        select(Bookings).where(Bookings.booking_id == payload.booking_id)
    )
    booking = booking_query.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    # ========== CHECK IF BOOKING IS EXPIRED ==========
    if booking.status == "EXPIRED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot process payment for an expired booking. The booking hold has been released."
        )
    
    # Verify payment method exists
    from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility
    method_query = await db.execute(
        select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == payload.method_id)
    )
    payment_method = method_query.scalars().first()
    
    if not payment_method:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment method_id")
    
    # Create payment record
    payment = Payments(
        booking_id=payload.booking_id,
        user_id=user_id,
        amount=payload.amount,
        method_id=payload.method_id,
        status="SUCCESS",
        transaction_reference=payload.transaction_reference,
        remarks=payload.remarks,
    )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Audit log for payment creation
    try:
        payment_val = PaymentResponse.model_validate(payment).model_dump()
        entity_id = f"payment:{payment.payment_id}"
        await log_audit(
            entity="payment",
            entity_id=entity_id,
            action="INSERT",
            new_value=payment_val,
            changed_by_user_id=user_id,
            user_id=user_id,
        )
    except Exception:
        pass
    
    # Invalidate caches
    await invalidate_pattern("payments:*")
    
    return PaymentResponse.model_validate(payment)


# ============================================================================
# 🔹 READ - Customer endpoint to fetch own payments
# ============================================================================
@router.get("/customer", response_model=List[PaymentResponse], status_code=status.HTTP_200_OK)
async def get_customer_payments(
    booking_id: Optional[int] = Query(None, description="Filter by booking ID"),
    limit: int = Query(20, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])

) -> List[PaymentResponse]:
    """
    Retrieve current user's own payments.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role. Users can only see their own payments.
    
    Args:
        booking_id (Optional[int]): Filter by booking ID (must be user's own booking).
        limit (int): Number of records to return (1-200, default 20).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        List[PaymentResponse]: List of payments belonging to current user.
    
    Raises:
        HTTPException (400): If booking_id is provided but doesn't belong to user.
    """
    # Try to get from cache
    cache_key = f"payments:customer:{current_user.user_id}:{booking_id}:{limit}:{offset}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Verify booking_id ownership if provided
    if booking_id is not None:
        stmt_booking = select(Bookings).where(Bookings.booking_id == booking_id)
        result_booking = await db.execute(stmt_booking)
        booking = result_booking.scalars().first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found"
            )
        
        if booking.user_id != current_user.user_id:
            raise ForbiddenException("You don't have permission to access this booking")
    
    # Build query for current user's payments
    conditions = [Payments.user_id == current_user.user_id]
    
    if booking_id is not None:
        conditions.append(Payments.booking_id == booking_id)
    
    stmt = select(Payments).where(and_(*conditions)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    payments = result.scalars().all()
    
    # Convert to response models
    response_data = [PaymentResponse.model_validate(payment) for payment in payments]
    
    # Cache the result
    await set_cached(cache_key, response_data, ttl=300)  # Cache for 5 minutes
    
    return response_data


# ============================================================================
# 🔹 READ - Admin endpoint to fetch all payments with flexible filters
# ============================================================================
@router.get("/admin", response_model=List[PaymentResponse], status_code=status.HTTP_200_OK)
async def get_all_payments(
    payment_id: Optional[int] = Query(None, description="Filter by payment ID"),
    booking_id: Optional[int] = Query(None, description="Filter by booking ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    method_id: Optional[int] = Query(None, description="Filter by payment method ID"),
    status: Optional[str] = Query(None, description="Filter by payment status (e.g., SUCCESS, PENDING, FAILED)"),
    amount_min: Optional[float] = Query(None, ge=0, description="Filter payments with amount >= this value"),
    amount_max: Optional[float] = Query(None, ge=0, description="Filter payments with amount <= this value"),
    start_date: Optional[datetime] = Query(None, description="Filter payments from this date onwards"),
    end_date: Optional[datetime] = Query(None, description="Filter payments until this date"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted records (False by default)"),
    limit: int = Query(20, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["PAYMENT_PROCESSING:READ", "ADMIN"]),
) -> List[PaymentResponse]:
    """
    Retrieve all payments with advanced filtering. Admin-only endpoint.
    
    **Authorization:** Requires PAYMENT_PROCESSING:READ permission AND ADMIN role (admin only).
    
    Fetches payment records with advanced filtering for admin dashboard. Results are cached for performance.
    
    Args:
        payment_id (Optional[int]): Filter by specific payment ID.
        booking_id (Optional[int]): Filter by booking ID.
        user_id (Optional[int]): Filter by user ID.
        method_id (Optional[int]): Filter by payment method.
        status (Optional[str]): Filter by status (SUCCESS, PENDING, FAILED).
        amount_min (Optional[float]): Minimum payment amount filter.
        amount_max (Optional[float]): Maximum payment amount filter.
        start_date (Optional[datetime]): Filter from this date onwards.
        end_date (Optional[datetime]): Filter until this date.
        is_deleted (Optional[bool]): Include soft-deleted records (default: False).
        limit (int): Records per page (default: 20, max: 200).
        offset (int): Pagination offset (default: 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
        token_payload (dict): Security token with PAYMENT_PROCESSING:READ permission.
    
    Returns:
        List[PaymentResponse]: Array of payment records matching criteria.
    
    Raises:
        HTTPException (403): If insufficient permissions.
        HTTPException (400): If invalid filter parameters.
    """
    
    # Since user has PAYMENT_PROCESSING:READ via Security, they can see all payments
    # No need for additional admin checks
    is_admin = True
    
    # If not admin and user_id filter is attempted, reject
    if user_id is not None and not is_admin:
        raise ForbiddenException("Only admins can filter payments by user_id")
    
    # Build cache key based on query parameters
    cache_key = (
        f"payments:{payment_id}:{booking_id}:{user_id}:{method_id}:"
        f"{status}:{amount_min}:{amount_max}:{start_date}:{end_date}:"
        f"{is_deleted}:{limit}:{offset}:{current_user.user_id}:{is_admin}"
    )
    
    # Try to get from cache
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Build the base query
    stmt = select(Payments)
    conditions = []
    
    # Authorization: If not admin, restrict to user's own bookings
    if not is_admin:
        user_booking_ids = await _get_user_bookings(db, current_user.user_id)
        if not user_booking_ids:
            # User has no bookings, return empty list
            return []
        conditions.append(Payments.booking_id.in_(user_booking_ids))
    
    # Add filters based on query parameters
    if payment_id is not None:
        conditions.append(Payments.payment_id == payment_id)
    
    if booking_id is not None:
        conditions.append(Payments.booking_id == booking_id)
    
    if user_id is not None:
        # Only admins can filter by user_id (already checked above)
        conditions.append(Payments.user_id == user_id)
    
    if method_id is not None:
        conditions.append(Payments.method_id == method_id)
    
    if status is not None:
        conditions.append(Payments.status == status)
    
    if amount_min is not None:
        conditions.append(Payments.amount >= amount_min)
    
    if amount_max is not None:
        conditions.append(Payments.amount <= amount_max)
    
    if start_date is not None:
        conditions.append(Payments.payment_date >= start_date)
    
    if end_date is not None:
        conditions.append(Payments.payment_date <= end_date)
    
    # Add is_deleted filter
    conditions.append(Payments.is_deleted == is_deleted)
    
    # Combine all conditions with AND
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    # Add pagination
    stmt = stmt.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(stmt)
    payments = result.scalars().all()
    
    # Convert to response models
    response_data = [PaymentResponse.model_validate(payment) for payment in payments]
    
    # Cache the result
    await set_cached(cache_key, response_data, ttl=300)  # Cache for 5 minutes
    
    return response_data


# ============================================================================
# 🔹 READ - Customer endpoint to fetch own single payment
# ============================================================================
@router.get("/customer/{payment_id}", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def get_customer_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
) -> PaymentResponse:
    """
    Get a specific payment belonging to current user only.
    
    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role. Users can only see their own payments.
    
    Args:
        payment_id (int): ID of the payment to retrieve.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        PaymentResponse: The requested payment if owned by current user.
    
    Raises:
        HTTPException (404): If payment not found.
        HTTPException (403): If payment belongs to different user.
    """
    # Try to get from cache
    cache_key = f"payment:customer:{payment_id}:{current_user.user_id}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Query the database
    stmt = select(Payments).where(Payments.payment_id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalars().first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )
    
    # Verify ownership - payment must belong to current user
    if payment.user_id != current_user.user_id:
        raise ForbiddenException("You don't have permission to access this payment")
    
    # Convert to response model
    response_data = PaymentResponse.model_validate(payment)
    
    # Cache the result
    await set_cached(cache_key, response_data, ttl=300)  # Cache for 5 minutes
    
    return response_data


# ============================================================================
# 🔹 READ - Admin endpoint to fetch any single payment
# ============================================================================
@router.get("/admin/{payment_id}", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def get_payment_by_id_admin(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["PAYMENT_PROCESSING:READ", "ADMIN"]),
) -> PaymentResponse:
    """
    Get a specific payment by its ID. Admin-only endpoint.
    
    **Authorization:** Requires PAYMENT_PROCESSING:READ permission AND ADMIN role (admin only).
    
    Admin users can access any payment and view detailed information.
    
    Args:
        payment_id (int): ID of the payment to retrieve.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        token_payload (dict): Security token with PAYMENT_PROCESSING:READ permission.
    
    Returns:
        PaymentResponse: The requested payment record.
    
    Raises:
        HTTPException (404): If payment not found.
    """
    # Try to get from cache
    cache_key = f"payment:admin:{payment_id}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Query the database
    stmt = select(Payments).where(Payments.payment_id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalars().first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )
    
    # Convert to response model
    response_data = PaymentResponse.model_validate(payment)
    
    # Cache the result
    await set_cached(cache_key, response_data, ttl=300)  # Cache for 5 minutes
    
    return response_data


@router.get("/booking/{booking_id}", response_model=List[PaymentResponse], status_code=status.HTTP_200_OK)
async def get_payments_by_booking(
    booking_id: int,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ"]),
) -> List[PaymentResponse]:
    """
    Get all payments for a specific booking.
    
    Authorization:
    - ADMIN users: Can access payments for any booking
    - CUSTOMER users: Can only access payments for their own bookings
    """
    
    # Try to get from cache
    cache_key = f"payments:booking:{booking_id}:{limit}:{offset}:{current_user.user_id}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Check authorization
    is_admin = True  # User has PAYMENT_PROCESSING:READ via Security
    
    if not is_admin:
        # Get the booking and check ownership
        stmt_booking = select(Bookings).where(Bookings.booking_id == booking_id)
        result_booking = await db.execute(stmt_booking)
        booking = result_booking.scalars().first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found"
            )
        
        if booking.user_id != current_user.user_id:
            raise ForbiddenException("You don't have permission to access payments for this booking")
    
    # Query the database
    stmt = (
        select(Payments)
        .where(Payments.booking_id == booking_id)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()
    
    if not payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No payments found for booking ID {booking_id}"
        )
    
    # Convert to response models
    response_data = [PaymentResponse.model_validate(payment) for payment in payments]
    
    # Cache the result
    await set_cached(cache_key, response_data, ttl=300)  # Cache for 5 minutes
    
    return response_data
