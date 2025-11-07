from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, List,Tuple
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
    """
    booking_id: int
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
        description="Mapping of room_id -> requested new room_type_id by customer",
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