from pydantic import BaseModel,Field,ConfigDict
from datetime import datetime




class RoleCreate(BaseModel):
    role_name:str
    role_description:str

class Role(RoleCreate):
    role_id:int
    model_config={"from_attributes":True}

class RoleResponse(Role):
    message: str = "Role created successfully"
    