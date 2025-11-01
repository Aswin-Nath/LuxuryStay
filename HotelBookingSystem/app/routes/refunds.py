from fastapi import APIRouter, Depends, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.refunds import RefundCreate, RefundResponse, RefundTransactionUpdate
from app.models.pydantic_models.refunds import RefundRoomMapCreate
from app.services.refunds_service import cancel_booking_and_create_refund as svc_cancel_booking, update_refund_transaction as svc_update_refund
from app.dependencies.authentication import get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.users import Users


router = APIRouter(prefix="/api", tags=["REFUNDS"])


@router.post("/bookings/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(booking_id: int, payload: RefundCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_cancel_booking(db, booking_id, payload, current_user)
    return RefundResponse.model_validate(obj)


@router.put("/refunds/{refund_id}/transaction", response_model=RefundResponse)
async def complete_refund(refund_id: int, payload: RefundTransactionUpdate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), _ok: bool = Depends(ensure_not_basic_user)):
    # Admin-only endpoint to update refund transaction details and status (restricted fields only)
    obj = await svc_update_refund(db, refund_id, payload, current_user)
    return RefundResponse.model_validate(obj)
