from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime


class BookingCreate(BaseModel):
    customer_id: int
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


class BookingResponse(BaseModel):
    booking_id: int
    customer_id: int
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
    created_at: datetime
    updated_at: datetime
    primary_customer_name: Optional[str]
    primary_customer_phone_number: Optional[str]
    primary_customer_dob: Optional[date]

    model_config = {"from_attributes": True}


class BookingRoomMapCreate(BaseModel):
    booking_id: int
    room_id: int
    room_type_id: int
    adults: int = Field(..., ge=1)
    children: Optional[int] = 0
    offer_discount_percent: Optional[float] = 0.0


class BookingRoomMapResponse(BookingRoomMapCreate):
    is_removed: bool
    removed_at: Optional[datetime]
    modified_in_edit_id: Optional[int]

    model_config = {"from_attributes": True}


class BookingTaxMapCreate(BaseModel):
    booking_id: int
    tax_id: int
    tax_amount: float


class BookingTaxMapResponse(BookingTaxMapCreate):
    created_at: datetime

    model_config = {"from_attributes": True}
