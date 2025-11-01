from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RefundCreate(BaseModel):
	booking_id: int
	user_id: int
	type: str
	refund_amount: float = Field(..., ge=0)
	transaction_method_id: int
	transaction_number: Optional[str] = None
	# refund_rooms should be a list of room IDs that were part of the booking
	refund_rooms: Optional[List[int]] = None
	remarks: Optional[str] = None


class RefundResponse(BaseModel):
	refund_id: int
	booking_id: int
	user_id: int
	type: str
	status: str
	refund_amount: float
	initiated_at: datetime
	processed_at: Optional[datetime]
	completed_at: Optional[datetime]
	remarks: Optional[str]
	is_deleted: bool
	transaction_method_id: int
	transaction_number: Optional[str]

	model_config = {"from_attributes": True}


class RefundRoomMapCreate(BaseModel):
	refund_id: int
	booking_id: int
	room_id: int
	refund_amount: float


class RefundRoomMapResponse(RefundRoomMapCreate):
	model_config = {"from_attributes": True}

