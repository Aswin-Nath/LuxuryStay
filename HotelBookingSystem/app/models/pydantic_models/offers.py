# ==============================================================
# app/models/pydantic_models/offers.py
# Purpose: Pydantic models for Offers Management
# ==============================================================

from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List, Any
from decimal import Decimal
from app.models.pydantic_models.room import RoomType


# ==============================================================
# OFFER ROOM MAP RESPONSE MODEL
# ==============================================================
class OfferRoomMapBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_type_id: int
    actual_price: Decimal = Field(..., ge=0, description="Original room price")
    discounted_price: Decimal = Field(..., ge=0, description="Discounted offer price")
    # include nested room type details for convenience in responses
    room_type: Optional[RoomType] = None


# ==============================================================
# OFFER INPUT MODEL (for creation)
# ==============================================================
class OfferCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    offer_items: Optional[List[Any]] = Field(default_factory=list, description="Array of perks/features")
    discount_percent: Decimal = Field(..., ge=0, le=100, description="Percentage discount applied")
    start_date: date
    expiry_date: date
    room_types: List[int] = Field(..., description="Room type IDs under this offer")
    offer_price:int

# ==============================================================
# OFFER OUTPUT MODEL
# ==============================================================
class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    offer_price:int
    offer_id: int
    offer_name: str
    description: Optional[str]
    offer_items: Optional[List[Any]]
    discount_percent: Decimal
    start_date: date
    expiry_date: date
    created_by: Optional[int]
    created_at: Optional[datetime] = None
    is_deleted: bool
    room_mappings: Optional[List[OfferRoomMapBase]] = Field(default_factory=list)

# ------------------------------------------------------------------
# Room type shape used when embedding room type data into Offer responses
# ------------------------------------------------------------------
# Note: use the canonical RoomType pydantic model defined in `app.models.pydantic_models.room`.
