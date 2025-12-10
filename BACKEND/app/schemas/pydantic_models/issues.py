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
	room_ids: Optional[List[int]] = None
	title: str = Field(..., max_length=200)
	description: str

	@model_validator(mode="before")
	def normalize_empty_room_ids(cls, values):
		# values may be a dict when coming via as_form or already a model
		if not isinstance(values, dict):
			return values
		# Handle empty list or string
		room_ids = values.get("room_ids")
		if room_ids == "" or room_ids == "[]" or (isinstance(room_ids, list) and len(room_ids) == 0):
			values["room_ids"] = None
		return values

	@classmethod
	def as_form(
		cls,
		booking_id: int = Form(...),
		room_ids: Optional[str] = Form(None),
		title: str = Form(...),
		description: str = Form(...),
	):
		# Parse room_ids string to list if provided
		parsed_room_ids = None
		if room_ids and room_ids != "" and room_ids != "[]":
			try:
				import json
				parsed_room_ids = json.loads(room_ids) if isinstance(room_ids, str) else room_ids
			except (json.JSONDecodeError, ValueError):
				parsed_room_ids = None
		return cls(booking_id=booking_id, room_ids=parsed_room_ids, title=title, description=description)


class IssueResponse(BaseModel):
	issue_id: int
	booking_id: int
	room_ids: Optional[List[int]] = None
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
	room_ids: Optional[List[int]] = None
	title: Optional[str] = None
	description: Optional[str] = None
	# When provided, images will replace the existing images unless caller uses append semantics
	images: Optional[List[str]] = None

