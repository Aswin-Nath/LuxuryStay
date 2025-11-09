"""
Notifications utilities.
"""

from datetime import datetime
from typing import Optional, List


def truncate_message(message: str, max_length: int = 200) -> str:
    """Truncate notification message."""
    if not message:
        return ""
    return message[:max_length].strip()


def should_send_notification(user_preferences: dict, notification_type: str) -> bool:
    """Check if notification should be sent based on user preferences."""
    if not user_preferences or notification_type not in user_preferences:
        return True
    return user_preferences.get(notification_type, True)


def format_notification_time(sent_at: datetime) -> str:
    """Format notification timestamp."""
    if not sent_at:
        return "Unknown"
    now = datetime.utcnow()
    delta = now - sent_at
    
    if delta.days > 0:
        return f"{delta.days} days ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600} hours ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60} minutes ago"
    else:
        return "Just now"
