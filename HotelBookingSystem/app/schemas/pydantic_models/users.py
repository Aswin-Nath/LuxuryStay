from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from fastapi import Form


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    phone_number: Optional[str] = None
    role_id: Optional[int] = 1


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
    refresh_token: str
    role_id:int
    model_config = {"from_attributes": True}