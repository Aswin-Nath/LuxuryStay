"""
Booking management utilities.
"""

from datetime import datetime, timedelta
from typing import Optional


def calculate_stay_duration(check_in: datetime, check_out: datetime) -> int:
    """Calculate number of nights between check-in and check-out."""
    if not check_in or not check_out:
        return 0
    delta = check_out - check_in
    return max(0, delta.days)


def calculate_total_price(nightly_rate: float, nights: int, taxes: float = 0.0) -> float:
    """Calculate total booking price."""
    if nights < 1 or nightly_rate < 0:
        return 0.0
    subtotal = nightly_rate * nights
    return subtotal + taxes


def is_future_date(date: datetime) -> bool:
    """Check if date is in the future."""
    if not date:
        return False
    return date > datetime.utcnow()


def is_valid_booking_dates(check_in: datetime, check_out: datetime) -> bool:
    """Validate booking dates."""
    if not check_in or not check_out:
        return False
    return check_out > check_in
