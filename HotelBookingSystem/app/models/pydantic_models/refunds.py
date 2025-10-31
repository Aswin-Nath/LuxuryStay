from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RefundCreate(BaseModel):
	booking_id: int
	customer_id: int
	type: str
	refund_amount: float = Field(..., ge=0)
	remarks: Optional[str] = None
	transaction_method: str
	transaction_number: Optional[str] = None


class RefundResponse(BaseModel):
	refund_id: int
	booking_id: int
	customer_id: int
	type: str
	status: str
	refund_amount: float
	initiated_at: datetime
	processed_at: Optional[datetime]
	completed_at: Optional[datetime]
	remarks: Optional[str]
	is_deleted: bool
	transaction_method: str
	transaction_number: Optional[str]

	model_config = {"from_attributes": True}


class RefundRoomMapCreate(BaseModel):
	refund_id: int
	booking_id: int
	room_id: int
	refund_amount: float


class RefundRoomMapResponse(RefundRoomMapCreate):
	model_config = {"from_attributes": True}

