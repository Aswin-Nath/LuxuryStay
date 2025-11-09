from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.payments import Payments
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.schemas.pydantic_models.payments import PaymentResponse
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.cache import get_cached, set_cached
from app.core.exceptions import ForbiddenError


router = APIRouter(prefix="/payments", tags=["PAYMENTS"])


async def _is_admin_or_has_payment_access(
    current_user: Users,
    user_permissions: dict,
) -> bool:
    """
    Check if user is admin or has payment processing permissions.
    Returns True if user can view all payments, False if restricted to own payments.
    """
    # Check if user has PAYMENT_PROCESSING READ or WRITE permission (admin access)
    has_payment_permission = (
        Resources.PAYMENT_PROCESSING.value in user_permissions
        and (
            PermissionTypes.READ.value in user_permissions[Resources.PAYMENT_PROCESSING.value]
            or PermissionTypes.WRITE.value in user_permissions[Resources.PAYMENT_PROCESSING.value]
        )
    )
    return has_payment_permission


async def _get_user_bookings(db: AsyncSession, user_id: int) -> List[int]:
    """Get all booking IDs for a specific user."""
    stmt = select(Bookings.booking_id).where(Bookings.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================================
# 🔹 READ - Fetch payments with flexible filters (admin or own bookings)
# ============================================================================
@router.get("/", response_model=List[PaymentResponse], status_code=status.HTTP_200_OK)
async def get_payments(
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
    user_permissions: dict = Depends(get_user_permissions),
) -> List[PaymentResponse]:
    """
    Get payments with flexible filtering by various query parameters.
    
    Authorization:
    - Admin users (with PAYMENT_PROCESSING READ/WRITE): Can access all payments
    - Regular users: Can only see payments for their own bookings
    
    Query Parameters:
    - payment_id: Get a specific payment
    - booking_id: Get payments for a specific booking
    - user_id: Filter by user ID (admin only)
    - method_id: Get payments using a specific payment method
    - status: Filter by payment status
    - amount_min/amount_max: Filter by amount range
    - start_date/end_date: Filter by date range
    - is_deleted: Include/exclude deleted records
    - limit: Number of results (default: 20, max: 200)
    - offset: Pagination offset (default: 0)
    """
    
    # Check authorization
    is_admin = await _is_admin_or_has_payment_access(current_user, user_permissions)
    
    # If not admin and user_id filter is attempted, reject
    if user_id is not None and not is_admin:
        raise ForbiddenError("Only admins can filter payments by user_id")
    
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


@router.get("/{payment_id}", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def get_payment_by_id(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
) -> PaymentResponse:
    """
    Get a specific payment by its ID.
    
    Authorization:
    - Admin users: Can access any payment
    - Regular users: Can only access payments for their own bookings
    """
    
    # Try to get from cache
    cache_key = f"payment:{payment_id}:{current_user.user_id}"
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
    
    # Check authorization
    is_admin = await _is_admin_or_has_payment_access(current_user, user_permissions)
    
    if not is_admin:
        # Get the booking for this payment and check ownership
        stmt_booking = select(Bookings).where(Bookings.booking_id == payment.booking_id)
        result_booking = await db.execute(stmt_booking)
        booking = result_booking.scalars().first()
        
        if not booking or booking.user_id != current_user.user_id:
            raise ForbiddenError("You don't have permission to access this payment")
    
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
    user_permissions: dict = Depends(get_user_permissions),
) -> List[PaymentResponse]:
    """
    Get all payments for a specific booking.
    
    Authorization:
    - Admin users: Can access payments for any booking
    - Regular users: Can only access payments for their own bookings
    """
    
    # Try to get from cache
    cache_key = f"payments:booking:{booking_id}:{limit}:{offset}:{current_user.user_id}"
    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result
    
    # Check authorization
    is_admin = await _is_admin_or_has_payment_access(current_user, user_permissions)
    
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
            raise ForbiddenError("You don't have permission to access payments for this booking")
    
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

