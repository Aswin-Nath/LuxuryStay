from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NotificationCreate(BaseModel):
	recipient_user_id: int = Field(..., alias="resc_user_id")
	notification_type: str
	entity_type: Optional[str] = None
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
	is_deleted: bool

	model_config = {"from_attributes": True}
