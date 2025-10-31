from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class IssueStatus(str, Enum):
	PENDING = "PENDING"
	IN_PROGRESS = "IN_PROGRESS"
	RESOLVED = "RESOLVED"
	CLOSED = "CLOSED"


class IssueCreate(BaseModel):
	booking_id: int
	room_id: Optional[int] = None
	user_id: int
	title: str = Field(..., max_length=200)
	description: str
	images: Optional[List[str]] = []


class IssueResponse(BaseModel):
	issue_id: int
	booking_id: int
	room_id: Optional[int] = None
	user_id: int
	title: str
	description: str
	images: List[str]
	status: IssueStatus
	reported_at: datetime
	resolved_at: Optional[datetime] = None
	last_updated: datetime
	is_deleted: bool
	resolved_by: Optional[int] = None

	model_config = {"from_attributes": True}


class IssueChatCreate(BaseModel):
	issue_id: int
	sender_id: int
	message: str


class IssueChatResponse(BaseModel):
	chat_id: int
	issue_id: int
	sender_id: int
	message: str
	sent_at: datetime
	is_deleted: bool

	model_config = {"from_attributes": True}

