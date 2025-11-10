from pydantic import BaseModel, Field, conint
from typing import Optional, Literal, Dict, List, Tuple
from datetime import date, datetime

class BookingEditBase(BaseModel):
    booking_id: int
    user_id: int
    primary_customer_name: str = Field(..., max_length=150)
    primary_customer_phno: str = Field(..., max_length=20)
    primary_customer_dob: date
    check_in_date: date
    check_out_date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    total_price: Optional[float] = Field(None, gt=0)
    edit_type: Optional[Literal["PRE", "POST"]] = None
    requested_by: Optional[int] = None

    requested_room_changes: Optional[Dict[int, int]] = Field(
        None,
        description="Mapping of room_id -> requested new room_type_id by customer"
    )

    model_config = {"from_attributes": True}


class BookingEditCreate(BaseModel):
    """Used when user submits a new edit request.

    This model intentionally does NOT accept `user_id` (it will be derived from the authenticated user).
    All fields are optional - only changed fields need to be provided. Unchanged fields can be omitted
    and the system will keep the existing values.
    
    edit_type is calculated automatically based on original booking check-in date:
    - PRE: If today < booking.check_in (before check-in, only room changes allowed)
    - POST: If today >= booking.check_in (after check-in, no changes allowed)
    
    total_price is automatically calculated based on room changes:
    - new_total = booking.total_price + (new_room_type_price - old_room_price) * num_nights
    """
    booking_id: int
    primary_customer_name: Optional[str] = Field(None, max_length=150)
    primary_customer_phno: Optional[str] = Field(None, max_length=20)
    primary_customer_dob: Optional[date] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    requested_by: Optional[int] = None

    requested_room_changes: Optional[Dict[int, int]] = Field(
        None,
        description="Mapping of room_id (current) -> room_type_id (new). Example: {5: 2, 10: 3}",
    )

    model_config = {"from_attributes": True}


class BookingEditResponse(BookingEditBase):
    edit_id: int
    status_id: Optional[int]
    edit_status: str
    reviewed_by: Optional[int]
    requested_at: Optional[datetime]
    processed_at: Optional[datetime]
    lock_expires_at: Optional[datetime]
    is_deleted: bool

    model_config = {"from_attributes": True}


class ReviewPayload(BaseModel):
    # Map of booking_room_map.room_id -> list of available room_ids suggested by admin
    suggested_rooms: Optional[Dict[int, List[int]]] = Field(
        None, description="Mapping of room_map_id -> suggested room IDs by admin"
    )
    note: Optional[str] = None


class DecisionPayload(BaseModel):
    note: Optional[str] = None
    room_decisions: Dict[int, Tuple[Literal["ACCEPT", "KEEP", "REFUND"], int]] = Field(
        ...,
        description=(
            "Mapping of room_id -> (decision, room_id). "
            "Example: {2: ('ACCEPT', 101), 5: ('KEEP', -1), 7: ('REFUND', -1)}"
        )
    )


class RoomOccupancyUpdate(BaseModel):
    """Individual room occupancy update within a booking."""
    room_id: int = Field(..., description="Room ID in the booking to update")
    adults: conint(ge=1) = Field(..., description="Number of adults (minimum 1 required)")
    children: conint(ge=0) = Field(..., description="Number of children (minimum 0 allowed)")

    model_config = {"from_attributes": True}


class UpdateRoomOccupancyRequest(BaseModel):
    """Request body for updating room occupancy (adults/children count) in a booking."""
    room_updates: List[RoomOccupancyUpdate] = Field(
        ..., description="List of room occupancy updates"
    )

    model_config = {"from_attributes": True}