from pydantic import BaseModel, Field
from typing import List


# ==============================
# PERMISSIONS SCHEMAS
# ==============================
class PermissionCreate(BaseModel):
    resource: str
    permission_type: str


class Permission(BaseModel):
    permission_id: int
    permission_name: str
    model_config = {"from_attributes": True}


class PermissionResponse(Permission):
    message: str = "Permission created successfully"


# ==============================
# PERMISSION ↔ ROLE MAP SCHEMAS
# ==============================
class RolePermissionAssign(BaseModel):
    role_id: int
    permission_ids: List[int]  # e.g. [1, 2, 5, 7]


class RolePermissionResponse(BaseModel):
    role_id: int
    assigned_permission_ids: List[int]
    message: str = "Permissions assigned successfully"

    model_config = {"from_attributes": True}
