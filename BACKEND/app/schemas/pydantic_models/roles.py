from pydantic import BaseModel,Field,ConfigDict
from datetime import datetime
from typing import Optional




class RoleCreate(BaseModel):
    role_name:str
    role_description: Optional[str] = None

class Role(RoleCreate):
    role_id:int
    model_config={"from_attributes":True}

class RoleResponse(Role):
    message: str = "Role created successfully"
    