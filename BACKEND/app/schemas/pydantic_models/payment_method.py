from pydantic import BaseModel, Field
from typing import Optional


class PaymentMethodCreate(BaseModel):
    name: str = Field(..., max_length=50)


class PaymentMethodResponse(BaseModel):
    method_id: int
    name: str

    model_config = {"from_attributes": True}
