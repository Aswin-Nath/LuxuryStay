from fastapi import APIRouter, Depends, Security, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.cache import invalidate_pattern, get_cached, set_cached
from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundResponse, RefundTransactionUpdate
from app.services.refunds_service import update_refund_transaction as svc_update_refund
from app.crud.refunds import fetch_refund_by_id, fetch_refunds_filtered
from app.models.sqlalchemy_schemas.refunds import Refunds
from datetime import datetime
from app.dependencies.authentication import get_current_user, check_permission
from app.models.sqlalchemy_schemas.users import Users
from app.utils.audit_util import log_audit
from pydantic import BaseModel

router = APIRouter(prefix="/refunds", tags=["REFUNDS"])


# ============================================================================
# 📋 PAGINATION RESPONSE MODEL
# ============================================================================
class PaginatedRefundResponse(BaseModel):
    """Paginated response wrapper for refund lists"""
    total: int
    page: int
    limit: int
    total_pages: int
    data: list[RefundResponse]


# ============================================================================
# 🔹 UPDATE - Process/complete a refund transaction
# ============================================================================
@router.put("/{refund_id}", response_model=RefundResponse)
async def complete_refund(
    refund_id: int,
    payload: RefundTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["REFUND_APPROVAL:WRITE", "ADMIN"]),
):
    """
    Update refund transaction and process refund status.
    
    Admin-only endpoint to update refund transaction details including payment method,
    transaction number, and refund status. Automatically sets processed_at and completed_at
    timestamps based on status transitions. Invalidates refund caches and logs audit entry.

    **Authorization:** Requires REFUND_APPROVAL:WRITE permission AND ADMIN role.
    
    Args:
        refund_id (int): The ID of the refund to update
        payload (RefundTransactionUpdate): Request body containing status, transaction_method_id, transaction_number
        db (AsyncSession): Database session dependency
        current_user (Users): Current authenticated admin user
        _permissions (dict): REFUND_APPROVAL:WRITE permission check
    
    Returns:
        RefundResponse: Updated refund record with new status and transaction details
    """
    refund_record = await svc_update_refund(db, refund_id, payload, current_user)
    
    # Invalidate refund caches
    await invalidate_pattern("refunds:*")
    await invalidate_pattern(f"refund:{refund_id}")
    
    # Audit refund transaction update
    try:
        new_val = RefundResponse.model_validate(refund_record).model_dump()
        entity_id = f"refund:{refund_id}"
        await log_audit(
            entity="refund",
            entity_id=entity_id,
            action="UPDATE",
            new_value=new_val,
            changed_by_user_id=getattr(current_user, 'user_id', None),
            user_id=getattr(current_user, 'user_id', None)
        )
    except Exception:
        pass
    
    return RefundResponse.model_validate(refund_record)


# ============================================================================
# 🔹 READ - List customer's own refunds (with pagination)
# ============================================================================
@router.get("/customer/list", response_model=PaginatedRefundResponse)
async def list_customer_refunds(
    booking_id: int | None = None,
    status: str | None = None,
    type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Retrieve current user's own refunds list with pagination.

    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role. 
    Users can only see their own refunds.
    
    Args:
        booking_id (Optional[int]): Filter by booking ID
        status (Optional[str]): Filter by refund status (INITIATED, PROCESSING, COMPLETED, etc.)
        type (Optional[str]): Filter by refund type
        from_date (Optional[datetime]): Filter refunds initiated on or after this date
        to_date (Optional[datetime]): Filter refunds initiated on or before this date
        page (int): Page number (1-based, default 1)
        limit (int): Records per page (1-100, default 10)
        db (AsyncSession): Database session
        current_user (Users): Authenticated user
    
    Returns:
        PaginatedRefundResponse: Paginated list of current user's refunds
    
    Example:
        GET /refunds/customer/list?page=1&limit=10
        GET /refunds/customer/list?status=COMPLETED&page=1&limit=20
    """
    # Validate pagination parameters
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10
    
    offset = (page - 1) * limit
    
    # Build cache key
    cache_key = (
        f"refunds:customer:{current_user.user_id}:list:"
        f"booking={booking_id}:status={status}:type={type}:"
        f"from={from_date}:to={to_date}:page={page}:limit={limit}"
    )
    
    # Try to get from cache
    cached = await get_cached(cache_key, PaginatedRefundResponse)
    if cached:
        return cached
    
    # Get total count
    count_stmt = select(func.count(Refunds.refund_id)).where(
        Refunds.user_id == current_user.user_id,
        Refunds.is_deleted.is_(False)
    )
    
    if booking_id:
        count_stmt = count_stmt.where(Refunds.booking_id == booking_id)
    if status:
        count_stmt = count_stmt.where(Refunds.status == status)
    if type:
        count_stmt = count_stmt.where(Refunds.type == type)
    if from_date:
        count_stmt = count_stmt.where(Refunds.initiated_at >= from_date)
    if to_date:
        count_stmt = count_stmt.where(Refunds.initiated_at <= to_date)
    
    total = await db.scalar(count_stmt) or 0
    
    # Get refunds with filters
    refunds = await fetch_refunds_filtered(
        db,
        booking_id=booking_id,
        user_id=current_user.user_id,
        status=status,
        type=type,
        from_date=from_date,
        to_date=to_date,
    )
    
    # Apply pagination (sort by initiated_at descending)
    refunds = sorted(refunds, key=lambda r: r.initiated_at, reverse=True)
    paginated_refunds = refunds[offset:offset + limit]
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    response = PaginatedRefundResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        data=[RefundResponse.model_validate(r) for r in paginated_refunds],
    )
    
    # Cache for 60 seconds
    await set_cached(cache_key, response, ttl=60)
    
    return response


# ============================================================================
# 🔹 READ - Get single customer refund (detail view)
# ============================================================================
@router.get("/customer/{refund_id}", response_model=RefundResponse)
async def get_customer_refund(
    refund_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Get detailed view of a single customer's refund.

    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role.
    Customer can only see their own refunds.
    
    Args:
        refund_id (int): The refund ID to retrieve
        db (AsyncSession): Database session
        current_user (Users): Authenticated customer user
    
    Returns:
        RefundResponse: Complete refund details
    
    Raises:
        HTTPException (404): Refund not found or customer doesn't have access
    """
    # Try cache first
    cache_key = f"refund:detail:{refund_id}"
    cached = await get_cached(cache_key, RefundResponse)
    if cached:
        return cached
    
    refund = await fetch_refund_by_id(db, refund_id)
    
    if not refund or refund.user_id != current_user.user_id or refund.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    response = RefundResponse.model_validate(refund)
    
    # Cache for 5 minutes
    await set_cached(cache_key, response, ttl=300)
    
    return response


# ============================================================================
# 🔹 READ - List all refunds (ADMIN only - with pagination)
# ============================================================================
@router.get("/admin/list", response_model=PaginatedRefundResponse)
async def list_admin_refunds(
    booking_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["REFUND_APPROVAL:READ", "ADMIN"]),
):
    """
    Retrieve all refunds across all customers with pagination (ADMIN only).

    **Authorization:** Requires REFUND_APPROVAL:READ permission AND ADMIN role.
    
    Args:
        booking_id (Optional[int]): Filter by booking ID
        user_id (Optional[int]): Filter by customer user ID
        status (Optional[str]): Filter by refund status
        type (Optional[str]): Filter by refund type
        from_date (Optional[datetime]): Filter refunds from date onwards
        to_date (Optional[datetime]): Filter refunds up to date
        page (int): Page number (1-based, default 1)
        limit (int): Records per page (1-100, default 10)
        db (AsyncSession): Database session
        current_user (Users): Authenticated admin user
    
    Returns:
        PaginatedRefundResponse: Paginated list of all refunds
    
    Example:
        GET /refunds/admin/list?page=1&limit=20
        GET /refunds/admin/list?status=COMPLETED&user_id=5&page=1
    """
    # Validate pagination parameters
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10
    
    offset = (page - 1) * limit
    
    # Build cache key
    cache_key = (
        f"refunds:admin:list:"
        f"booking={booking_id}:user={user_id}:status={status}:type={type}:"
        f"from={from_date}:to={to_date}:page={page}:limit={limit}"
    )
    
    # Try to get from cache
    cached = await get_cached(cache_key, PaginatedRefundResponse)
    if cached:
        return cached
    
    # Get total count
    count_stmt = select(func.count(Refunds.refund_id)).where(
        Refunds.is_deleted.is_(False)
    )
    
    if booking_id:
        count_stmt = count_stmt.where(Refunds.booking_id == booking_id)
    if user_id:
        count_stmt = count_stmt.where(Refunds.user_id == user_id)
    if status:
        count_stmt = count_stmt.where(Refunds.status == status)
    if type:
        count_stmt = count_stmt.where(Refunds.type == type)
    if from_date:
        count_stmt = count_stmt.where(Refunds.initiated_at >= from_date)
    if to_date:
        count_stmt = count_stmt.where(Refunds.initiated_at <= to_date)
    
    total = await db.scalar(count_stmt) or 0
    
    # Get refunds with filters
    refunds = await fetch_refunds_filtered(
        db,
        booking_id=booking_id,
        user_id=user_id,
        status=status,
        type=type,
        from_date=from_date,
        to_date=to_date,
    )
    
    # Apply pagination (sort by initiated_at descending)
    refunds = sorted(refunds, key=lambda r: r.initiated_at, reverse=True)
    paginated_refunds = refunds[offset:offset + limit]
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    response = PaginatedRefundResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        data=[RefundResponse.model_validate(r) for r in paginated_refunds],
    )
    
    # Cache for 60 seconds
    await set_cached(cache_key, response, ttl=60)
    
    return response


# ============================================================================
# 🔹 READ - Get single refund (ADMIN only - detail view)
# ============================================================================
@router.get("/admin/{refund_id}", response_model=RefundResponse)
async def get_admin_refund(
    refund_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["REFUND_APPROVAL:READ", "ADMIN"]),
):
    """
    Get detailed view of any refund in the system (ADMIN only).

    **Authorization:** Requires REFUND_APPROVAL:READ permission AND ADMIN role.
    
    Args:
        refund_id (int): The refund ID to retrieve
        db (AsyncSession): Database session
        current_user (Users): Authenticated admin user
    
    Returns:
        RefundResponse: Complete refund details with all transaction info
    
    Raises:
        HTTPException (404): Refund not found
    """
    # Try cache first
    cache_key = f"refund:admin:detail:{refund_id}"
    cached = await get_cached(cache_key, RefundResponse)
    if cached:
        return cached
    
    refund = await fetch_refund_by_id(db, refund_id)
    
    if not refund or refund.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    response = RefundResponse.model_validate(refund)
    
    # Cache for 5 minutes
    await set_cached(cache_key, response, ttl=300)
    
    return response
