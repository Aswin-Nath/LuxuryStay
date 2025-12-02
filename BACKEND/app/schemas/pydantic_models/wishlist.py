from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class WishlistCreate(BaseModel):
    room_type_id: Optional[int] = Field(None, ge=1, description="Room type ID (mutually exclusive with offer_id)")
    offer_id: Optional[int] = Field(None, ge=1, description="Offer ID (mutually exclusive with room_type_id)")
    item_type:str
    # @field_validator('room_type_id', 'offer_id')
    # @classmethod
    # def validate_at_least_one(cls, value, info):
    #     # Check if at least one is provided
    #     if not info.data.get('room_type_id') and not info.data.get('offer_id'):
    #         raise ValueError('Either room_type_id or offer_id must be provided')
    #     # Check if both are provided
    #     if info.data.get('room_type_id') and info.data.get('offer_id'):
    #         raise ValueError('Cannot provide both room_type_id and offer_id together')
    #     return value


class WishlistResponse(BaseModel):
    wishlist_id: int
    room_type_id: Optional[int]
    offer_id: Optional[int]
    wishlist_type: str
    added_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}
