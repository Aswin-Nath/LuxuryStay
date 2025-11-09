"""
Room management utilities.
"""

from typing import Dict, Any, Optional


def validate_room_availability(available_rooms: int) -> bool:
    """Check if room has availability."""
    return available_rooms > 0


def calculate_room_discount(base_price: float, discount_percent: float) -> float:
    """Calculate discounted room price."""
    if discount_percent < 0 or discount_percent > 100:
        return base_price
    return base_price * (1 - discount_percent / 100)


def format_room_type(room_type: str) -> str:
    """Standardize room type format."""
    return room_type.lower().strip() if room_type else ""


def is_valid_capacity(capacity: int) -> bool:
    """Validate room capacity."""
    return isinstance(capacity, int) and 1 <= capacity <= 100
