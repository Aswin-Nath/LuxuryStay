from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from fastapi import Form


class IssueStatus(str, Enum):
	PENDING = "PENDING"
	IN_PROGRESS = "IN_PROGRESS"
	RESOLVED = "RESOLVED"
	CLOSED = "CLOSED"


class IssueCreate(BaseModel):
	booking_id: int
	room_id: Optional[int] = None
	title: str = Field(..., max_length=200)
	description: str

	@model_validator(mode="before")
	def normalize_zero_to_none(cls, values):
		# values may be a dict when coming via as_form or already a model
		if not isinstance(values, dict):
			return values
		if values.get("room_id") == 0:
			values["room_id"] = None
		return values

	@classmethod
	def as_form(
		cls,
		booking_id: int = Form(...),
		room_id: Optional[int] = Form(None),
		title: str = Form(...),
		description: str = Form(...),
	):
		return cls(booking_id=booking_id, room_id=room_id, title=title, description=description)


class IssueResponse(BaseModel):
	issue_id: int
	booking_id: int
	room_id: Optional[int] = None
	user_id: int
	title: str
	description: str
	# images removed — handled via separate endpoints
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


class IssueUpdate(BaseModel):
	booking_id: Optional[int] = None
	room_id: Optional[int] = None
	title: Optional[str] = None
	description: Optional[str] = None
	# When provided, images will replace the existing images unless caller uses append semantics
	images: Optional[List[str]] = None

