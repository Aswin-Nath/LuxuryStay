from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ═══════════════════════════════════════════════════════════════
# LOCK ROOM REQUEST - Lock without guest details
# ═══════════════════════════════════════════════════════════════
class RoomLockRequest(BaseModel):
    """
    Request to lock a room.
    Guest details are NOT needed here - will be provided during booking confirmation.
    """
    room_type_id: int = Field(..., description="Room type to lock")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    expires_at: str = Field(..., description="Lock expiry time (ISO 8601)")


# ═══════════════════════════════════════════════════════════════
# ROOM LOCK RESPONSE
# ═══════════════════════════════════════════════════════════════
class RoomLockResponse(BaseModel):
    """
    Response when a room is successfully locked.
    Contains lock info and room details for frontend display.
    """
    lock_id: int
    room_id: int
    room_type_id: int
    type_name: str
    room_no: str
    check_in: str
    check_out: str
    expires_at: str
    price_per_night: float
    nights: int
    total_price: float
    max_adult_count: int
    max_child_count: int
    square_ft: int
    description: Optional[str]


# ═══════════════════════════════════════════════════════════════
# GUEST DETAILS FOR BOOKING CONFIRMATION
# ═══════════════════════════════════════════════════════════════
class RoomGuestDetails(BaseModel):
    """
    Guest details for a specific locked room.
    Provided during booking confirmation.
    """
    lock_id: int = Field(..., description="The lock_id of the room to assign guest details to")
    guest_name: str = Field(..., min_length=2, max_length=150, description="Primary guest name")
    guest_age: int = Field(..., ge=18, le=120, description="Primary guest age (18+)")
    adult_count: int = Field(..., ge=1, le=10, description="Number of adults staying")
    child_count: int = Field(default=0, ge=0, le=10, description="Number of children staying")
    special_requests: Optional[str] = Field(None, max_length=500, description="Special requests for this room")


# ═══════════════════════════════════════════════════════════════
# BOOKING CONFIRMATION REQUEST
# ═══════════════════════════════════════════════════════════════
class BookingConfirmRequest(BaseModel):
    """
    Complete booking confirmation with guest details for all rooms.
    Sent when user is ready to pay.
    """
    payment_method_id: int = Field(..., description="1=Card, 2=UPI, 3=NetBanking")
    rooms_guest_details: List[RoomGuestDetails] = Field(..., description="Guest details for each locked room")
    upi_id: Optional[str] = Field(None, description="UPI ID if payment_method_id is 2")


# ═══════════════════════════════════════════════════════════════
# BOOKING ROOM DETAIL - For response
# ═══════════════════════════════════════════════════════════════
class BookingRoomDetail(BaseModel):
    """
    Room details in booking confirmation response.
    """
    room_id: int
    room_no: str
    type_name: str
    check_in: date
    check_out: date
    nights: int
    price_per_night: float
    total_price: float
    # Guest information
    guest_name: str
    guest_age: int
    adult_count: int
    child_count: int
    special_requests: Optional[str]


# ═══════════════════════════════════════════════════════════════
# PAYMENT CONFIRMATION RESPONSE
# ═══════════════════════════════════════════════════════════════
class PaymentConfirmationResponse(BaseModel):
    """
    Complete booking and payment confirmation.
    Sent to frontend after successful payment and booking confirmation.
    """
    # Booking Details
    booking_id: int
    user_id: int
    check_in: date
    check_out: date
    total_nights: int
    booking_status: str
    created_at: datetime

    # Rooms in Booking
    rooms: List[BookingRoomDetail]
    room_count: int

    # Price Breakdown
    subtotal: float  # Sum of all room totals
    gst_18_percent: float
    total_amount: float

    # Payment Details
    payment_id: int
    payment_status: str
    payment_method: str  # "Credit/Debit Card", "UPI", or "Net Banking"
    transaction_reference: str
    transaction_date: datetime

    # Message
    message: str = "✅ Booking confirmed and payment successful! Your reservation is locked."
