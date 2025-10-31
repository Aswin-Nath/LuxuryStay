from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImageCreate(BaseModel):
	entity_type: str = Field(..., max_length=50)
	entity_id: int
	image_url: str
	caption: Optional[str] = None
	is_primary: Optional[bool] = False
	uploaded_by: Optional[int] = None


class ImageResponse(BaseModel):
	image_id: int
	entity_type: str
	entity_id: int
	image_url: str
	caption: Optional[str] = None
	is_primary: bool
	uploaded_by: Optional[int] = None
	created_at: datetime
	is_deleted: bool

	model_config = {"from_attributes": True}

