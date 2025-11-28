from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import date
from fastapi import Form
import re

ALLOWED_GENDERS = {"male", "female", "other"}

# simple length check only; complex rules handled in validators
PHONE_REGEX = r'^\+?\d{10,15}$'


class   UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: str = Field(..., pattern=PHONE_REGEX)
    dob: date
    gender: str
    role_id: int = Field(..., gt=1)

    @field_validator("role_id", mode="before")
    def validate_role_id(cls, value):
        # Convert string to int if needed
        if isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError("role_id must be a valid integer")
        if value <= 1:
            raise ValueError("role_id must be greater than 1")
        return value
    
    # --- DOB VALIDATION ---
    @field_validator('dob')
    def dob_must_be_in_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError('Date of birth must be in the past.')
        return value

    # --- PASSWORD VALIDATION ---
    @field_validator('password')
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if not any(c.islower() for c in value):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not any(c.isupper() for c in value):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not any(c.isdigit() for c in value):
            raise ValueError('Password must contain at least one digit.')
        if not any(not c.isalnum() for c in value):
            raise ValueError('Password must contain at least one special character.')
        return value

    # --- GENDER VALIDATION ---
    @field_validator('gender')
    def gender_must_be_valid(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError('Gender is required.')
        normalized = value.strip().lower()
        if normalized not in ALLOWED_GENDERS:
            raise ValueError('Gender must be Male, Female, or Other.')
        return normalized.title()

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role_id: int

    model_config = {"from_attributes": True}


class ProfileResponse(UserResponse):
    profile_image_url:Optional[str]=None
    dob: Optional[date] = None
    gender: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None

class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role_id: int

    model_config = {"from_attributes": True}