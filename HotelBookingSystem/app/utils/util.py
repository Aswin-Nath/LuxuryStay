"""
Common utilities used across the application.
These are general-purpose helpers available for reuse.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


def get_current_utc_time() -> datetime:
    """Get current UTC time."""
    return datetime.utcnow()


def dict_to_model(data: Dict[str, Any], model_class):
    """Convert dictionary to Pydantic model."""
    if hasattr(model_class, "model_validate"):
        return model_class.model_validate(data)
    return model_class(**data)


def model_to_dict(model: Any) -> Dict[str, Any]:
    """Convert Pydantic model to dictionary."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict() if hasattr(model, "dict") else dict(model)


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    return data.get(key, default) if isinstance(data, dict) else default


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    return len(parts) == 2 and parts[0] and parts[1]


def paginate(items: list, page: int, page_size: int) -> tuple:
    """Paginate a list of items. Returns (items, total, pages)."""
    if page < 1:
        page = 1
    total = len(items)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total, pages


def flatten_dict(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def enum_to_list(enum_class: type) -> list:
    """Convert Enum class to list of values."""
    if not issubclass(enum_class, Enum):
        return []
    return [e.value for e in enum_class]
