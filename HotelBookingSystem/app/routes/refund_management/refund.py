from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundResponse, RefundTransactionUpdate
from app.services.refunds_service.refunds_service import update_refund_transaction as svc_update_refund, get_refund as svc_get_refund, list_refunds as svc_list_refunds
from datetime import datetime
from app.dependencies.authentication import get_current_user, ensure_not_basic_user
from app.dependencies.authentication import get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.users import Users


router = APIRouter(prefix="/api", tags=["REFUNDS"])



@router.put("/refunds/{refund_id}/transaction", response_model=RefundResponse)
async def complete_refund(refund_id: int, payload: RefundTransactionUpdate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), _ok: bool = Depends(ensure_not_basic_user)):
    # Admin-only endpoint to update refund transaction details and status (restricted fields only)
    obj = await svc_update_refund(db, refund_id, payload, current_user)
    # invalidate refund caches
    from app.core.cache import invalidate_pattern
    await invalidate_pattern("refunds:*")
    await invalidate_pattern(f"refund:{refund_id}")
    return RefundResponse.model_validate(obj)


@router.get("/refunds/{refund_id}", response_model=RefundResponse)
async def get_single_refund(refund_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Return a single refund. Owners can fetch their refunds; others require elevated role.

    Basic users (role_id == 1) may only fetch refunds they own. Non-basic users (admins/staff)
    can fetch any refund.
    """
    obj = await svc_get_refund(db, refund_id)

    # Allow owner or non-basic users
    if getattr(current_user, "user_id", None) != getattr(obj, "user_id", None):
        # if user is basic (role_id == 1) deny
        if getattr(current_user, "role_id", None) == 1:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to view this refund")

    return RefundResponse.model_validate(obj)


@router.get("/refunds", response_model=list[RefundResponse])
async def query_refunds(
    refund_id: int | None = None,
    booking_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Flexible getter for refunds. Query by any combination of fields. Returns list of matching refunds.

    Access rules: basic users (role_id == 1) may only query refunds they own (user_id filter enforced).
    Admin/staff may query across users.
    """
    # Enforce that basic users can only query their own refunds
    if getattr(current_user, "role_id", None) == 1:
        # If user_id filter is supplied and doesn't match current user, reject
        if user_id is not None and user_id != current_user.user_id:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to query other users' refunds")
        user_id = current_user.user_id

    items = await svc_list_refunds(db, refund_id=refund_id, booking_id=booking_id, user_id=user_id, status=status, type=type, from_date=from_date, to_date=to_date)
    # caching queries by parameters could be expensive; keep simple: cache common queries
    from app.core.cache import get_cached, set_cached
    cache_key = f"refunds:query:refund_id:{refund_id}:booking_id:{booking_id}:user_id:{user_id}:status:{status}:type:{type}:from:{from_date}:to:{to_date}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    result = [RefundResponse.model_validate(i) for i in items]
    await set_cached(cache_key, result, ttl=60)
    return result
