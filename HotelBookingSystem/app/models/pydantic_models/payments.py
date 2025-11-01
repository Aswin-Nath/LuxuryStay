from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    booking_id: int
    user_id: int
    amount: float = Field(..., ge=0)
    payment_date: Optional[datetime] = None
    method_id: int
    # status is not expected from client; payments are one-time and created as SUCCESS
    transaction_reference: Optional[str] = None
    remarks: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: int
    booking_id: int
    user_id: Optional[int]
    amount: float
    payment_date: datetime
    method_id: int
    status: str
    transaction_reference: Optional[str]
    remarks: Optional[str]
    is_deleted: bool

    model_config = {"from_attributes": True}
