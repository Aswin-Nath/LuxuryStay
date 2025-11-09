"""
Reviews management utilities.
"""

from typing import Optional


def validate_rating(rating: int) -> bool:
    """Validate review rating (typically 1-5)."""
    return isinstance(rating, int) and 1 <= rating <= 5


def truncate_review_comment(comment: str, max_length: int = 1000) -> str:
    """Truncate review comment to max length."""
    if not comment:
        return ""
    return comment[:max_length].strip()


def is_helpful_review(helpful_count: int, total_count: int, threshold: float = 0.5) -> bool:
    """Check if review is considered helpful."""
    if total_count == 0:
        return False
    return (helpful_count / total_count) >= threshold


def rating_to_stars(rating: int) -> str:
    """Convert numeric rating to star representation."""
    if not validate_rating(rating):
        return ""
    return "⭐" * rating
