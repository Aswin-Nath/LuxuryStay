from fastapi import APIRouter, Depends, Query, HTTPException, status
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
# Consolidated GET endpoint for permissions
# Supports three modes (provide exactly one):
#  - role_id -> returns permissions assigned to a role
#  - resources (list) -> returns permissions for the given resources
#  - permission_id -> returns roles assigned to that permission
# ==============================================================
@permissions_router.get("/")
async def get_permissions(
    permission_id: int | None = Query(None, description="Permission id to fetch roles for"),
    role_id: int | None = Query(None, description="Role id to fetch permissions for"),
    resources: List[str] | None = Query(None, description="List of resources to filter by"),
    db: AsyncSession = Depends(get_db),
):
    # Require at least one filter and only one at a time to avoid ambiguous responses
    provided = sum(x is not None for x in (permission_id, role_id, resources))
    if provided == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide one of: permission_id, role_id or resources")
    if provided > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide only one of: permission_id, role_id or resources at a time")

    if permission_id is not None:
        roles = await svc_get_roles_for_permission(db, permission_id)
        return {
            "permission_id": permission_id,
            "roles": [{"role_id": r.role_id, "role_name": r.role_name} for r in roles],
            "message": "Roles fetched successfully",
        }

    if role_id is not None:
        permissions = await svc_get_permissions_by_role(db, role_id)
        return [PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"}) for p in permissions]

    # resources is not None
    permissions = await svc_get_permissions_by_resources(db, resources or [])
    return [PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"}) for p in permissions]