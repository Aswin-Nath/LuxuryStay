from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    booking_id: int
    amount: float = Field(..., ge=0)
    method: str
    transaction_reference: Optional[str] = None
    remarks: Optional[str] = None
    user_id: Optional[int] = None


class PaymentResponse(BaseModel):
    payment_id: int
    booking_id: int
    amount: float
    payment_date: datetime
    method: str
    status: str
    transaction_reference: Optional[str]
    remarks: Optional[str]
    is_deleted: bool
    user_id: Optional[int]

    model_config = {"from_attributes": True}
