from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.pydantic_models.images import ImageResponse


class ReviewBase(BaseModel):
    booking_id: int
    # For booking-only reviews this will be None; for room-type reviews it must be provided
    room_type_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5, description="Rating between 1 and 5")
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    """Model used when creating a review. The authenticated user is expected to be the reviewer."""
    pass


class ReviewUpdate(BaseModel):
    """Model used by a user to update their review. Only rating and comment are editable by the reviewer."""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating between 1 and 5")
    comment: Optional[str] = None


class ReviewResponse(ReviewBase):
    review_id: int
    user_id: int
    admin_id: Optional[int] = None
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    images: Optional[List[ImageResponse]] = []
    # Pydantic v2: allow constructing from ORM/SQLAlchemy objects
    model_config = {"from_attributes": True}


class AdminResponseCreate(BaseModel):
    """Payload used by admins to post a response to a review."""
    admin_response: str
