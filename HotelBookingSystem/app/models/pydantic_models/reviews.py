from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReviewBase(BaseModel):
    booking_id: int
    # For booking-only reviews this will be None; for room-type reviews it must be provided
    room_type_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5, description="Rating between 1 and 5")
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    """Model used when creating a review. The authenticated user is expected to be the reviewer."""
    pass


class ReviewResponse(ReviewBase):
    review_id: int
    user_id: int
    admin_id: Optional[int] = None
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    class Config:
        orm_mode = True
