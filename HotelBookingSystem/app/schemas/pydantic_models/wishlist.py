from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WishlistCreate(BaseModel):
    user_id: int
    room_type_id: Optional[int] = None
    offer_id: Optional[int] = None


class WishlistResponse(BaseModel):
    wishlist_id: int
    user_id: int
    room_type_id: Optional[int]
    offer_id: Optional[int]
    added_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}
