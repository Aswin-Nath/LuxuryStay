# ==============================================================
# app/models/pydantic_models/room.py
# Purpose: Pydantic models for Room Management module
# ==============================================================
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# ==============================================================
# ENUMS
# ==============================================================
class RoomStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"
    FROZEN = "FROZEN"


class FreezeReason(str, Enum):
    NONE = "NONE"
    CLEANING = "CLEANING"
    ADMIN_LOCK = "ADMIN_LOCK"
    SYSTEM_HOLD = "SYSTEM_HOLD"

# ==============================================================
# ROOM TYPES
# ==============================================================
class RoomTypeCreate(BaseModel):
    type_name: str = Field(..., max_length=50)
    max_adult_count: int = Field(..., ge=1)
    max_child_count: int = Field(0, ge=0)
    price_per_night: float = Field(..., ge=0)
    description: Optional[str] = None
    square_ft: int = Field(..., ge=0)

    model_config = {"from_attributes": True}


class RoomTypeResponse(RoomTypeCreate):
    room_type_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoomType(BaseModel):
    room_type_id: int
    type_name: str
    price_per_night: float
    max_adult_count: int
    max_child_count: int
    square_ft: int

    model_config = {"from_attributes": True}

# ==============================================================
# ROOMS
# ==============================================================
class RoomCreate(BaseModel):
    room_no: str = Field(..., max_length=20)
    room_type_id: int
    # price_per_night, max_adult_count and max_child_count are derived from
    # the selected RoomType and should not be provided when creating a Room.
    room_status: Optional[RoomStatus] = RoomStatus.AVAILABLE
    freeze_reason: Optional[FreezeReason] = None

    model_config = {"from_attributes": True}




class RoomResponse(BaseModel):
    room_id: int
    room_no: str
    room_type_id: int
    # these are returned (populated from DB / room type)
    price_per_night: float
    max_adult_count: int
    max_child_count: int
    room_status: RoomStatus
    freeze_reason: Optional[FreezeReason]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Room(BaseModel):
    room_id: int
    room_no: str
    room_type_id: int
    price_per_night: float
    room_status: RoomStatus
    freeze_reason: Optional[FreezeReason]
    max_adult_count: int
    max_child_count: int

    model_config = {"from_attributes": True}

# ==============================================================
# ROOM AMENITIES
# ==============================================================
class AmenityCreate(BaseModel):
    amenity_name: str = Field(..., max_length=100)

    model_config = {"from_attributes": True}


class AmenityResponse(AmenityCreate):
    amenity_id: int

    model_config = {"from_attributes": True}


class Amenity(BaseModel):
    amenity_id: int
    amenity_name: str

    model_config = {"from_attributes": True}

# ==============================================================
# ROOM AMENITY MAP
# ==============================================================
class RoomAmenityMapCreate(BaseModel):
    room_id: int
    amenity_id: int

    model_config = {"from_attributes": True}


class RoomAmenityMapResponse(RoomAmenityMapCreate):
    model_config = {"from_attributes": True}


class RoomAmenityMap(BaseModel):
    room_id: int
    amenity_id: int

    model_config = {"from_attributes": True}


# ==============================================================
# UPDATE MODELS (all fields optional to allow partial updates)
# ==============================================================
class RoomTypeUpdate(BaseModel):
    type_name: Optional[str] = None
    max_adult_count: Optional[int] = None
    max_child_count: Optional[int] = None
    price_per_night: Optional[float] = None
    description: Optional[str] = None
    square_ft: Optional[int] = None

    model_config = {"from_attributes": True}


class RoomUpdate(BaseModel):
    room_no: Optional[str] = None
    room_type_id: Optional[int] = None
    room_status: Optional[RoomStatus] = None
    freeze_reason: Optional[FreezeReason] = None

    model_config = {"from_attributes": True}