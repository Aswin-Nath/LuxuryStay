from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class NotificationCreate(BaseModel):
	model_config = ConfigDict(populate_by_name=True)
	
	recipient_user_id: int = Field(..., alias="resc_user_id")
	notification_type: Literal["SYSTEM", "PROMOTIONAL", "REMINDER", "TRANSACTIONAL", "SECURITY", "OTHER"]
	entity_type: Optional[
		Literal[
			"BOOKING",
			"PAYMENT",
			"REFUND",
			"ISSUE",
			"REVIEW",
			"WISHLIST",
			"USER_ACCOUNT",
			"SYSTEM",
			"ROOM"
		]
	] = None
	entity_id: Optional[int] = None
	title: str
	message: str


class NotificationResponse(BaseModel):
	notification_id: int
	recipient_user_id: int
	notification_type: str
	entity_type: Optional[str]
	entity_id: Optional[int]
	title: str
	message: str
	is_read: bool
	created_at: datetime
	read_at: Optional[datetime] = None
	is_deleted: bool

	model_config = {"from_attributes": True}
