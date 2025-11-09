"""
Payment & Refund utilities.
"""

from decimal import Decimal
from typing import Optional


def validate_amount(amount: float) -> bool:
    """Validate payment amount."""
    return isinstance(amount, (int, float)) and amount > 0


def calculate_refund_amount(original_amount: float, refund_percent: float) -> float:
    """Calculate refund amount based on percentage."""
    if refund_percent < 0 or refund_percent > 100:
        return 0.0
    return original_amount * (refund_percent / 100)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string."""
    if amount is None:
        return f"0.00 {currency}"
    return f"{amount:.2f} {currency}"


def is_valid_transaction_id(transaction_id: str) -> bool:
    """Validate transaction ID format."""
    return bool(transaction_id) and len(transaction_id) >= 5
