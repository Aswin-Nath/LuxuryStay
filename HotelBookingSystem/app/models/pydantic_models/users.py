from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    role_id:int
    model_config = {"from_attributes": True}
