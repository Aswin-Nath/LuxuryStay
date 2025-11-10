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
# 🔹 READ - Fetch refund details (single or list with filters)
# ============================================================================
@router.get("/", response_model=list[RefundResponse])
async def get_refunds(
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
):
    """
    Retrieve refunds with role-based access control and filtering.
    
    Unified endpoint supporting single refund retrieval and paginated list queries.
    Basic users (role_id == 1) can only access their own refunds; non-basic users
    (admin/manager) can query across all refunds. Results are cached for 60 seconds.
    
    Args:
        refund_id (Optional[int]): Query parameter - Specific refund ID to fetch.
        booking_id (Optional[int]): Query parameter - Filter by booking ID.
        user_id (Optional[int]): Query parameter - Filter by refund owner user ID.
        status (Optional[str]): Query parameter - Filter by refund status.
        type (Optional[str]): Query parameter - Filter by refund type.
        from_date (Optional[datetime]): Query parameter - Filter refunds from date onwards.
        to_date (Optional[datetime]): Query parameter - Filter refunds up to date.
        limit (int): Query parameter - Maximum records to return (default 20).
        offset (int): Query parameter - Number of records to skip (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Current authenticated user (required).
    
    Returns:
        list[RefundResponse]: List of refund records matching filters and pagination.
    
    Raises:
        HTTPException (403): If basic user tries to access other users' refunds or
                             if basic user requests refund_id of another user.
    
    Access Rules:
        - Basic users: Can only view their own refunds (user_id auto-set to current user).
        - Non-basic users: Can query all refunds with any combination of filters.
        - Single refund fetch: If refund_id provided, returns that one refund (after auth check).
        - List fetch: Returns paginated results with limit and offset.
    
    Caching:
        - Results cached in Redis with 60-second TTL using cache key:
          `refunds:query:refund_id:{refund_id}:booking_id:{booking_id}:...`
    
    Example:
        GET /refunds/?user_id=5&status=COMPLETED&limit=10&offset=0
    """
    """Unified GET for refunds.

    Rules:
    - If `refund_id` provided -> return that refund (basic users can only access their own).
    - Basic users (role_id == 1) can only query their refunds (user_id derived from token).
    - Non-basic users can query across all refunds. If no filters provided, return paginated list.
    """

    is_basic_user = getattr(current_user, "role_id", None) == 1

    # If a specific refund id requested, fetch and enforce ownership for basic users
    if refund_id is not None:
        refund_record = await svc_get_refund(db, refund_id)
        if is_basic_user and getattr(refund_record, "user_id", None) != current_user.user_id:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to view this refund")
        return [RefundResponse.model_validate(refund_record)]

    # Enforce that basic users can only query their own refunds
    if is_basic_user:
        if user_id is not None and user_id != current_user.user_id:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to query other users' refunds")
        user_id = current_user.user_id

    # Build cache key and fetch
    from app.core.cache import get_cached, set_cached
    cache_key = f"refunds:query:refund_id:{refund_id}:booking_id:{booking_id}:user_id:{user_id}:status:{status}:type:{type}:from:{from_date}:to:{to_date}:limit:{limit}:offset:{offset}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_refunds(db, refund_id=refund_id, booking_id=booking_id, user_id=user_id, status=status, type=type, from_date=from_date, to_date=to_date)

    # Simple pagination
    paginated = items[offset: offset + limit] if offset or limit else items

    result = [RefundResponse.model_validate(i) for i in paginated]
    await set_cached(cache_key, result, ttl=60)
    return result
