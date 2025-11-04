from fastapi import APIRouter, Depends,Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.postgres_connection import get_db
from app.models.pydantic_models.permissions import PermissionResponse,RolePermissionAssign,RolePermissionResponse
from app.services.roles_and_permissions_service.permissions_service import (
    assign_permissions_to_role as svc_assign_permissions_to_role,
    get_permissions_by_role as svc_get_permissions_by_role,
    get_permissions_by_resources as svc_get_permissions_by_resources,
    get_roles_for_permission as svc_get_roles_for_permission,
)

permissions_router = APIRouter(prefix="/permissions", tags=["PERMISSIONS"])



# ==============================================================
# 2️⃣ ASSIGN PERMISSIONS TO A ROLE
# ==============================================================
@permissions_router.post("/assign", response_model=RolePermissionResponse)
async def assign_permissions_to_role(payload: RolePermissionAssign, db: AsyncSession = Depends(get_db)):
    res = await svc_assign_permissions_to_role(db, payload.role_id, payload.permission_ids)
    return RolePermissionResponse.model_validate(res)


# ==============================================================
# 3️⃣ GET PERMISSIONS BY ROLE_ID
# ==============================================================
@permissions_router.get("/by-role/{role_id}", response_model=List[PermissionResponse])
async def get_permissions_by_role(role_id: int, db: AsyncSession = Depends(get_db)):
    permissions = await svc_get_permissions_by_role(db, role_id)
    return [PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"}) for p in permissions]


# ==============================================================
# 4️⃣ GET PERMISSIONS BY MULTIPLE RESOURCES
# ==============================================================
@permissions_router.get("/by-resources", response_model=List[PermissionResponse])
async def get_permissions_by_resources(
    resources: List[str] = Query(..., description="List of resources to filter by"),
    db: AsyncSession = Depends(get_db)
):
    permissions = await svc_get_permissions_by_resources(db, resources)
    return [PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"}) for p in permissions]


# ==============================================================
# 5️⃣ GET ROLES ASSIGNED TO A PERMISSION
# ==============================================================
@permissions_router.get("/{permission_id}/roles")
async def get_roles_for_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    roles = await svc_get_roles_for_permission(db, permission_id)
    return {
        "permission_id": permission_id,
        "roles": [{"role_id": r.role_id, "role_name": r.role_name} for r in roles],
        "message": "Roles fetched successfully",
    }