"""
Offers/Promotions utilities.
"""

from datetime import datetime
from typing import Optional


def is_offer_active(start_date: datetime, end_date: datetime) -> bool:
    """Check if offer is currently active."""
    if not start_date or not end_date:
        return False
    now = datetime.utcnow()
    return start_date <= now <= end_date


def calculate_offer_discount(base_price: float, discount_type: str, discount_value: float) -> float:
    """Calculate price with offer applied."""
    if base_price <= 0:
        return base_price
    
    if discount_type == "percentage":
        if 0 <= discount_value <= 100:
            return base_price * (1 - discount_value / 100)
    elif discount_type == "fixed":
        if discount_value > 0:
            return max(0, base_price - discount_value)
    
    return base_price


def is_offer_expired(end_date: datetime) -> bool:
    """Check if offer has expired."""
    if not end_date:
        return True
    return datetime.utcnow() > end_date


def validate_offer_code(code: str) -> bool:
    """Validate offer/coupon code format."""
    if not code:
        return False
    return len(code) >= 3 and len(code) <= 20
