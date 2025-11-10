from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundResponse, RefundTransactionUpdate
from app.services.refunds_service import update_refund_transaction as svc_update_refund, get_refund as svc_get_refund, list_refunds as svc_list_refunds
from datetime import datetime
from app.dependencies.authentication import get_current_user, check_permission
from app.models.sqlalchemy_schemas.users import Users
from app.utils.audit_util import log_audit


router = APIRouter(prefix="/refunds", tags=["REFUNDS"])



# ============================================================================
# 🔹 UPDATE - Process/complete a refund transaction
# ============================================================================
@router.put("/{refund_id}", response_model=RefundResponse)
async def complete_refund(
    refund_id: int,
    payload: RefundTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["REFUND_APPROVAL:WRITE"]),
):
    """
    Update refund transaction and process refund status.
    
    Admin-only endpoint to update refund transaction details including payment method,
    transaction number, and refund status. Automatically sets processed_at and completed_at
    timestamps based on status transitions. Invalidates refund caches and logs audit entry.
    
    **Authorization:** Requires REFUND_APPROVAL:WRITE permission.
    
    Args:
        refund_id (int): Path parameter - The ID of the refund to update.
        payload (RefundTransactionUpdate): Request body containing status, transaction_method_id, transaction_number.
        db (AsyncSession): Database session dependency.
        current_user (Users): Current authenticated admin user (required).
        _permissions (dict): REFUND_APPROVAL:WRITE permission check.
    
    Returns:
        RefundResponse: Updated refund record with new status and transaction details.
    
    Raises:
        HTTPException (403): If user lacks REFUND_APPROVAL:WRITE permission.
        HTTPException (404): If refund ID not found.
        HTTPException (400): If transaction_method_id is invalid.
    
    Example:
        PUT /refunds/123
        {
            "status": "COMPLETED",
            "transaction_method_id": 1,
            "transaction_number": "TXN123456"
        }
    """
    # Admin-only endpoint to update refund transaction details and status (restricted fields only)
    refund_record = await svc_update_refund(db, refund_id, payload, current_user)
    # invalidate refund caches
    from app.core.cache import invalidate_pattern
    await invalidate_pattern("refunds:*")
    await invalidate_pattern(f"refund:{refund_id}")
    # audit refund transaction update
    try:
        new_val = RefundResponse.model_validate(refund_record).model_dump()
        entity_id = f"refund:{refund_id}"
        await log_audit(entity="refund", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return RefundResponse.model_validate(refund_record)


# ============================================================================
# 🔹 READ - Customer endpoint to fetch own refunds
# ============================================================================
@router.get("/customer", response_model=list[RefundResponse])
async def get_customer_refunds(
    refund_id: int | None = None,
    booking_id: int | None = None,
    status: str | None = None,
    type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Retrieve current user's own refunds only.
    
    **Authorization:** No special scope required. Users can only see their own refunds.
    
    Args:
        refund_id (Optional[int]): Fetch specific refund (must belong to current user).
        booking_id (Optional[int]): Filter by booking ID (must belong to current user).
        status (Optional[str]): Filter by refund status.
        type (Optional[str]): Filter by refund type.
        from_date (Optional[datetime]): Filter refunds from date onwards.
        to_date (Optional[datetime]): Filter refunds up to date.
        limit (int): Maximum records to return (default 20).
        offset (int): Number of records to skip (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        list[RefundResponse]: List of current user's refunds matching filters.
    
    Raises:
        HTTPException (404): If refund_id not found or doesn't belong to user.
    """
    from app.core.cache import get_cached, set_cached
    from fastapi import HTTPException, status as http_status
    
    # If specific refund requested, verify ownership
    if refund_id is not None:
        refund_record = await svc_get_refund(db, refund_id)
        if getattr(refund_record, "user_id", None) != current_user.user_id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this refund"
            )
        return [RefundResponse.model_validate(refund_record)]
    
    # Build cache key for list query
    cache_key = f"refunds:customer:{current_user.user_id}:booking_id:{booking_id}:status:{status}:type:{type}:from:{from_date}:to:{to_date}:limit:{limit}:offset:{offset}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    
    # Fetch only current user's refunds
    items = await svc_list_refunds(
        db,
        refund_id=refund_id,
        booking_id=booking_id,
        user_id=current_user.user_id,  # ALWAYS filter by current user
        status=status,
        type=type,
        from_date=from_date,
        to_date=to_date
    )
    
    # Apply pagination
    paginated = items[offset : offset + limit] if offset or limit else items
    
    result = [RefundResponse.model_validate(i) for i in paginated]
    await set_cached(cache_key, result, ttl=60)
    return result


# ============================================================================
# 🔹 READ - Admin endpoint to fetch all refunds with advanced filtering
# ============================================================================
@router.get("/admin", response_model=list[RefundResponse])
async def get_admin_refunds(
    refund_id: int | None = None,
    booking_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["REFUND_APPROVAL:READ"]),
):
    """
    Retrieve all refunds with advanced filtering. Admin-only endpoint.
    
    **Authorization:** Requires REFUND_APPROVAL:READ permission (admin only).
    
    Admin users can query all refunds with any combination of filters including user_id.
    Results are cached for performance.
    
    Args:
        refund_id (Optional[int]): Filter by specific refund ID.
        booking_id (Optional[int]): Filter by booking ID.
        user_id (Optional[int]): Filter by refund owner user ID (admin only).
        status (Optional[str]): Filter by refund status.
        type (Optional[str]): Filter by refund type.
        from_date (Optional[datetime]): Filter refunds from date onwards.
        to_date (Optional[datetime]): Filter refunds up to date.
        limit (int): Maximum records to return (default 20).
        offset (int): Number of records to skip (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        _permissions (dict): Security token with REFUND_APPROVAL:READ permission.
    
    Returns:
        list[RefundResponse]: List of all refunds matching criteria.
    
    Raises:
        HTTPException (403): If insufficient permissions.
    """
    from app.core.cache import get_cached, set_cached
    
    # Build cache key for admin list query
    cache_key = f"refunds:admin:refund_id:{refund_id}:booking_id:{booking_id}:user_id:{user_id}:status:{status}:type:{type}:from:{from_date}:to:{to_date}:limit:{limit}:offset:{offset}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    
    # Fetch refunds with all filters (admin has no restrictions)
    items = await svc_list_refunds(
        db,
        refund_id=refund_id,
        booking_id=booking_id,
        user_id=user_id,  # Admin can filter by any user
        status=status,
        type=type,
        from_date=from_date,
        to_date=to_date
    )
    
    # Apply pagination
    paginated = items[offset : offset + limit] if offset or limit else items
    
    result = [RefundResponse.model_validate(i) for i in paginated]
    await set_cached(cache_key, result, ttl=60)
    return result
