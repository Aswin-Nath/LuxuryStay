from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any
from datetime import date, time, datetime
from app.schemas.pydantic_models.payments import BookingPaymentCreate


# ─────────────────────────────────────────────
# BOOKING CREATION
# ─────────────────────────────────────────────
class BookingCreate(BaseModel):
    rooms: Optional[List[int]] = []
    room_count: int = Field(..., ge=1)
    check_in: date
    check_in_time: Optional[time] = time(12, 0)
    check_out: date
    check_out_time: Optional[time] = time(11, 0)
    total_price: float
    offer_id: Optional[int] = None
    offer_discount_percent: Optional[float] = 0.0
    primary_customer_name: Optional[str] = None
    primary_customer_phone_number: Optional[str] = None
    primary_customer_dob: Optional[date] = None
    payment: Optional[BookingPaymentCreate] = None  # Optional payment info


# ─────────────────────────────────────────────
# BOOKING RESPONSE
# ─────────────────────────────────────────────
class BookingResponse(BaseModel):
    booking_id: int
    user_id: int
    room_count: int
    check_in: date
    check_in_time: time
    check_out: date
    check_out_time: time
    total_price: float
    offer_id: Optional[int]
    offer_discount_percent: float
    status: str
    is_deleted: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    primary_customer_name: Optional[str]
    primary_customer_phone_number: Optional[str]
    primary_customer_dob: Optional[date]
    rooms: Optional[List["BookingRoomMapResponse"]] = []
    taxes: Optional[List["BookingTaxMapResponse"]] = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# ROOM MAP MODELS
# ─────────────────────────────────────────────
class BookingRoomMapCreate(BaseModel):
    booking_id: int
    room_id: int
    room_type_id: int
    adults: int = Field(..., ge=1)
    children: Optional[int] = 0
    offer_discount_percent: Optional[float] = 0.0


class BookingRoomMapResponse(BookingRoomMapCreate):
    is_pre_edited_room: Optional[bool] = False
    is_post_edited_room: Optional[bool] = False
    is_room_active: Optional[bool] = True
    rating_given: Optional[int] = 0
    edit_suggested_rooms: Optional[Any] = None  # JSONB array of room_ids suggested by admin

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# TAX MAP MODELS
# ─────────────────────────────────────────────
class BookingTaxMapCreate(BaseModel):
    booking_id: int
    tax_id: int
    tax_amount: float


class BookingTaxMapResponse(BookingTaxMapCreate):
    created_at: datetime

    model_config = {"from_attributes": True}

