from pydantic import BaseModel,model_validator
from typing import Optional, List,Any
from datetime import datetime


class RefundCreate(BaseModel):
	"""Payload for cancelling a booking and requesting a refund.

	booking_id is supplied via the path parameter, and user_id is derived from the authenticated user.
	The body should contain only the minimal fields needed for a refund request.
	"""
	full_cancellation: Optional[bool] = False
	refund_amount: Optional[float] = None
	# refund_rooms should be a list of room IDs that were part of the booking
	refund_rooms: Optional[List[int]] = None
	remarks: Optional[str] = None
	transaction_method_id: Optional[int] = None
	transaction_number: Optional[str] = None
	@model_validator(mode="before")
	def normalize_zero_to_none(cls, values):
		if not isinstance(values, dict):
			return values
		if values.get("transaction_method_id") == 0:
			values["transaction_method_id"] = None
		return values
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
	transaction_method_id: Optional[int]
	transaction_number: Optional[str]
	# full_cancellation may not exist on older DB rows; keep optional for compatibility
	full_cancellation: Optional[bool] = False

	model_config = {"from_attributes": True}


class RefundRoomMapCreate(BaseModel):
	refund_id: int
	booking_id: int
	room_id: int
	refund_amount: float


class RefundRoomMapResponse(RefundRoomMapCreate):
	model_config = {"from_attributes": True}


class RefundTransactionUpdate(BaseModel):
	"""Admin payload to update refund transaction details.

	Only these fields are allowed to be changed by admin:
	- status
	- transaction_method_id
	- transaction_number
	"""
	status: Optional[str] = None
	transaction_method_id: Optional[int] = None
	transaction_number: Optional[str] = None

