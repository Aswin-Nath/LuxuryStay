from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal, Any
from datetime import date, time, datetime
import re


# ─────────────────────────────────────────────
# ROOM OCCUPANCY MODEL
# ─────────────────────────────────────────────
class RoomOccupancy(BaseModel):
    """
    Model for specifying occupancy details for a single room.
    
    Attributes:
        room_type_id (int): The ID of the room type to book.
        adults (int): Number of adults in this room (minimum 1).
        children (int): Number of children in this room (optional, minimum 0).
    
    Validation:
    - adults: Must be at least 1 (required in room)
    - children: Can be 0 or more
    """
    room_type_id: int
    adults: int = Field(..., ge=1, description="Number of adults (minimum 1 required per room)")
    children: int = Field(default=0, ge=0, description="Number of children (default 0)")


# ─────────────────────────────────────────────
# BOOKING CREATION
# ─────────────────────────────────────────────
class BookingCreate(BaseModel):
    """
    Request model for creating a new booking.
    
    room_count is automatically derived from the length of the rooms array.
    No need to provide it explicitly - it's computed via a validator.
    total_price is automatically calculated from room types and stay duration.
    
    Validation:
    - rooms: Must contain at least 1 room with occupancy details
    - check_in: Date object (validated against current date in service)
    - check_out: Date object (validated after check_in in service)
    - Each room must have at least 1 adult
    """
    rooms: List[RoomOccupancy] = Field(..., min_items=1, description="List of rooms to book with occupancy details. Each room must have at least 1 adult.")
    check_in: date
    check_in_time: Optional[time] = Field(default_factory=lambda: time(12, 0), description="Check-in time (default: 12:00)")
    check_out: date
    check_out_time: Optional[time] = Field(default_factory=lambda: time(11, 0), description="Check-out time (default: 11:00)")
    primary_customer_name: Optional[str] = None
    primary_customer_phone_number: Optional[str] = None
    primary_customer_dob: Optional[date] = None
    
    @property
    def room_count(self) -> int:
        """
        Computed property: Returns the number of rooms from the rooms array length.
        
        Automatically calculated from len(rooms). This allows the service layer to access
        room_count without requiring it as a separate input field.
        
        Returns:
            int: The length of the rooms array.
        """
        return len(self.rooms) if self.rooms else 0

    @field_validator('rooms')
    @classmethod
    def validate_rooms_have_adults(cls, rooms):
        """
        Validate that each room has at least one adult.
        
        Ensures booking compliance: every room must have a minimum of 1 adult occupant.
        
        Args:
            rooms (List[RoomOccupancy]): List of rooms with occupancy details.
        
        Returns:
            List[RoomOccupancy]: The validated rooms list.
        
        Raises:
            ValueError: If any room has 0 adults.
        """
        if not rooms:
            raise ValueError("At least one room must be specified")
        
        for idx, room in enumerate(rooms):
            if room.adults < 1:
                raise ValueError(f"Room {idx + 1} must have at least 1 adult. Got {room.adults} adult(s)")
        
        return rooms

    @property
    def room_type_ids(self) -> List[int]:
        """
        Get list of room type IDs from rooms.
        
        Returns:
            List[int]: List of room_type_id values from each room occupancy.
        """
        return [room.room_type_id for room in self.rooms]

    @field_validator('primary_customer_phone_number')
    @classmethod
    def validate_indian_phone_number(cls, v):
        """
        Validate Indian phone number format.
        
        Indian phone numbers can be:
        - 10 digits starting with 6, 7, 8, or 9 (e.g., 9876543210)
        - 10 digits with country code +91 (e.g., +919876543210)
        - 10 digits with leading 0 followed by 9 (e.g., 09876543210)
        
        Args:
            v (str): The phone number to validate.
        
        Returns:
            str: The validated phone number.
        
        Raises:
            ValueError: If phone number is not in valid Indian format.
        """
        if v is None:
            return v
        
        # Remove whitespace and hyphens
        phone = str(v).strip().replace(" ", "").replace("-", "")
        
        # Pattern for Indian phone numbers
        # Allows: +919876543210, 9876543210, 09876543210
        indian_phone_pattern = r'^(\+91|0)?[6-9]\d{9}$'
        
        if not re.match(indian_phone_pattern, phone):
            raise ValueError(
                'Invalid Indian phone number. Must be 10 digits starting with 6-9 '
                '(e.g., 9876543210, +919876543210, or 09876543210)'
            )
        
        return phone


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

