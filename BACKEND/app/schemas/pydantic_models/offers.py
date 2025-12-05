from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class RoomTypeOffer(BaseModel):
    """Single room type offer configuration"""
    room_type_id: int
    type_name: Optional[str] = None  # Room type name, populated on response
    original_price: Optional[Decimal] = None  # Original room type price before discount, populated on response
    price_per_night: Optional[Decimal] = None  # Discounted price per night, populated on response
    available_count: int = Field(..., gt=0, le=5, description="Number of rooms to allocate for this offer (max 5 total across all types)")
    discount_percent: Decimal = Field(..., ge=0, le=100, description="Discount percentage for this room type")


class OfferCreate(BaseModel):
    """Request payload to create a new offer"""
    offer_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    discount_percent: Decimal = Field(..., ge=0, le=100, description="Base discount percentage")
    room_types: List[RoomTypeOffer] = Field(
        ..., 
        description="Array of room types with available count and discount %"
    )
    is_active: bool = True
    valid_from: date
    valid_to: date
    max_uses: Optional[int] = Field(None, ge=1, description="NULL = unlimited")

    class Config:
        json_schema_extra = {
            "example": {
                "offer_name": "Summer Sale 2025",
                "description": "50% off select rooms",
                "discount_percent": 50,
                "room_types": [
                    {"room_type_id": 1, "available_count": 5, "discount_percent": 50},
                    {"room_type_id": 2, "available_count": 3, "discount_percent": 35},
                ],
                "is_active": True,
                "valid_from": "2025-06-01",
                "valid_to": "2025-08-31",
                "max_uses": 100
            }
        }


class OfferUpdate(BaseModel):
    """Request payload to update an offer"""
    offer_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    room_types: Optional[List[RoomTypeOffer]] = None
    is_active: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    max_uses: Optional[int] = Field(None, ge=1)

class OfferResponse(BaseModel):
    """Response payload for offer details"""
    offer_id: int
    offer_name: str
    description: Optional[str]
    discount_percent: Decimal
    room_types: List[RoomTypeOffer]
    is_active: bool
    valid_from: date
    valid_to: date
    max_uses: Optional[int]
    current_uses: int
    is_deleted: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_saved_to_wishlist: bool = False  # Whether current user has saved this to wishlist
    wishlist_id: Optional[int] = None  # Wishlist entry ID if user has saved this to wishlist

    class Config:
        from_attributes = True


class OfferListResponse(BaseModel):
    """Simplified offer response for listing"""
    offer_id: int
    offer_name: str
    description: Optional[str]
    discount_percent: Decimal
    is_active: bool
    valid_from: date
    valid_to: date
    current_uses: int
    max_uses: Optional[int]
    is_saved_to_wishlist: bool = False  # Whether current user has saved this to wishlist
    wishlist_id: Optional[int] = None  # Wishlist entry ID if user has saved this to wishlist

    class Config:
        from_attributes = True
