from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.refunds import RefundResponse, RefundTransactionUpdate
from app.services.refunds_service.refunds_service import update_refund_transaction as svc_update_refund
from app.dependencies.authentication import get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.users import Users


router = APIRouter(prefix="/api", tags=["REFUNDS"])



@router.put("/refunds/{refund_id}/transaction", response_model=RefundResponse)
async def complete_refund(refund_id: int, payload: RefundTransactionUpdate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), _ok: bool = Depends(ensure_not_basic_user)):
    # Admin-only endpoint to update refund transaction details and status (restricted fields only)
    obj = await svc_update_refund(db, refund_id, payload, current_user)
    return RefundResponse.model_validate(obj)
