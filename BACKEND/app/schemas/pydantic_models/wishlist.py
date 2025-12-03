from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class WishlistCreate(BaseModel):
    room_type_id: Optional[int] = Field(None, ge=1, description="Room type ID (mutually exclusive with offer_id)")
    offer_id: Optional[int] = Field(None, ge=1, description="Offer ID (mutually exclusive with room_type_id)")
    item_type: str


# ============================================================================
# 🔹 ROOM TYPE WISHLIST RESPONSE
# ============================================================================
class WishlistRoomResponse(BaseModel):
    """Wishlist response for room types with full room details and primary image"""
    wishlist_id: int
    room_type_id: int
    type_name: str
    price_per_night: Decimal
    description: Optional[str]
    square_ft: int
    max_adult_count: int
    max_child_count: int
    amenities: List[str] = []  # List of amenity names
    added_at: datetime
    primary_image: Optional[str] = None  # Primary image URL fetched from image service

    model_config = {"from_attributes": True}


# ============================================================================
# 🔹 OFFER WISHLIST RESPONSE
# ============================================================================
class WishlistOfferResponse(BaseModel):
    """Wishlist response for offers with key offer details and primary image"""
    wishlist_id: int
    offer_id: int
    offer_name: str
    description: Optional[str]
    discount_percent: Decimal
    valid_from: date
    valid_to: date
    room_types: List[dict] = []  # Array of {room_type_id, available_count, discount_percent}
    added_at: datetime
    primary_image: Optional[str] = None  # Primary image URL fetched from image service

    model_config = {"from_attributes": True}


# ============================================================================
# 🔹 GENERIC WISHLIST RESPONSE (for backward compatibility if needed)
# ============================================================================
class WishlistResponse(BaseModel):
    wishlist_id: int
    room_type_id: Optional[int]
    offer_id: Optional[int]
    wishlist_type: str
    added_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}
