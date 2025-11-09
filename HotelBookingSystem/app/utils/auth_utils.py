"""
Authentication utilities - with Indian phone format support.
"""

import re
from typing import Optional, Tuple


def is_valid_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    Returns: (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    email = email.strip().lower()
    
    # Basic email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check length
    if len(email) > 254:
        return False, "Email is too long (max 254 characters)"
    
    return True, None


def is_strong_password(password: str, min_length: int = 8) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?~`" for c in password)
    
    if not has_upper:
        return False, "Password must contain at least one uppercase letter"
    if not has_lower:
        return False, "Password must contain at least one lowercase letter"
    if not has_digit:
        return False, "Password must contain at least one digit"
    if not has_special:
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?~`)"
    
    return True, None


def is_valid_indian_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Indian phone number format.
    Accepts:
    - 10-digit numbers: 9XXXXXXXXX, 8XXXXXXXXX, 7XXXXXXXXX, 6XXXXXXXXX
    - With country code: +91-9XXXXXXXXX, +919XXXXXXXXX
    - With spaces/dashes: 91-9XXXXXXXXX, 91 9XXXXXXXXX
    Returns: (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number cannot be empty"
    
    phone = phone.strip()
    
    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-().]", "", phone)
    
    # Handle +91 country code
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91"):
        cleaned = cleaned[2:]
    
    # Validate: must be exactly 10 digits
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits (and optional formatting)"
    
    if len(cleaned) != 10:
        return False, "Phone number must be exactly 10 digits"
    
    # First digit must be 6, 7, 8, or 9 (Indian mobile standard)
    if cleaned[0] not in ["6", "7", "8", "9"]:
        return False, "Phone number must start with 6, 7, 8, or 9 (Indian format)"
    
    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format.
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must not exceed 50 characters"
    
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    
    return True, None


def is_valid_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Alias for is_valid_indian_phone for backward compatibility.
    """
    return is_valid_indian_phone(phone)
