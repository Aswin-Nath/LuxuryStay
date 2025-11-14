from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RoomMapItem(BaseModel):
    # keep generic fields — booking snapshots can vary. Add common attrs if known.
    room_id: Optional[int]
    room_number: Optional[str]
    rate: Optional[float]
    meta: Optional[Dict[str, Any]] = None


class BookingSnapshot(BaseModel):
    # Generic mapping for the booking snapshot. Keep flexible to accept arbitrary keys.
    data: Dict[str, Any] = Field(..., description="Full booking snapshot (arbitrary structure)")


class BookingLogModel(BaseModel):
    booking_id: int
    edit_id: int
    edit_type: str = Field(..., description="Type of edit that generated the log (e.g. 'PRE' or 'POST')")
    booking_snapshot: BookingSnapshot
    room_map_snapshot: Optional[List[RoomMapItem]] = Field(default_factory=list)
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    logged_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "booking_id": 123,
                "edit_id": 1,
                "edit_type": "PRE",
                "booking_snapshot": {"data": {"guest_name": "Alice", "dates": ["2025-01-01"]}},
                "room_map_snapshot": [{"room_id": 10, "room_number": "101", "rate": 120.0}],
                "approved_by": None,
                "approved_at": None,
                "logged_at": "2025-11-06T00:00:00Z",
            }
        }
