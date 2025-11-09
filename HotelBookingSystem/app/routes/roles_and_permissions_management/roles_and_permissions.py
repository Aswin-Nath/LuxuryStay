from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.permissions import PermissionResponse, RolePermissionAssign, RolePermissionResponse
from app.schemas.pydantic_models.roles import RoleCreate, RoleResponse
from app.services.roles_and_permissions_service.roles_and_permissions_service import (
    assign_permissions_to_role as svc_assign_permissions_to_role,
    get_permissions_by_role as svc_get_permissions_by_role,
    get_permissions_by_resources as svc_get_permissions_by_resources,
    get_roles_for_permission as svc_get_roles_for_permission,
    create_role as svc_create_role, list_roles as svc_list_roles
)
from app.dependencies.authentication import get_user_permissions, ensure_not_basic_user
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


# Single combined router
roles_and_permissions_router = APIRouter(prefix="/roles", tags=["ROLES"])


# ==============================================================
# 🔹 CREATE - Assign permissions to a role
# ==============================================================
# 2️⃣ ASSIGN PERMISSIONS TO A ROLE
# ==============================================================
@roles_and_permissions_router.post("/assign", response_model=RolePermissionResponse)
async def assign_permissions_to_role(payload: RolePermissionAssign, db: AsyncSession = Depends(get_db), _ok: bool = Depends(ensure_not_basic_user), user_perms: dict = Depends(get_user_permissions)):
    # Require ADMIN_CREATION:READ permission to access permissions assignment endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")
    assignment_result = await svc_assign_permissions_to_role(db, payload.role_id, payload.permission_ids)
    # audit permission assignment
    try:
        new_val = RolePermissionResponse.model_validate(assignment_result).model_dump()
        entity_id = f"role:{getattr(assignment_result, 'role_id', payload.role_id)}"
        await log_audit(entity="role_permissions", entity_id=entity_id, action="INSERT", new_value=new_val)
    except Exception:
        pass
    return RolePermissionResponse.model_validate(assignment_result)


# ==============================================================
# 🔹 READ - Fetch permissions by role, resource, or permission_id
# ==============================================================
# Consolidated GET endpoint for permissions
# Supports three modes (provide exactly one):
#  - role_id -> returns permissions assigned to a role
#  - resources (list) -> returns permissions for the given resources
#  - permission_id -> returns roles assigned to that permission
# ==============================================================
@roles_and_permissions_router.get("/permissions")
async def get_permissions(
    permission_id: int | None = Query(None, description="Permission id to fetch roles for"),
    role_id: int | None = Query(None, description="Role id to fetch permissions for"),
    resources: List[str] | None = Query(None, description="List of resources to filter by"),
    db: AsyncSession = Depends(get_db),
    _ok: bool = Depends(ensure_not_basic_user),
    user_perms: dict = Depends(get_user_permissions),
):
    # Require at least one filter and only one at a time to avoid ambiguous responses
    provided = sum(x is not None for x in (permission_id, role_id, resources))
    if provided == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide one of: permission_id, role_id or resources")
    if provided > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide only one of: permission_id, role_id or resources at a time")

    # Require ADMIN_CREATION:READ permission to access permissions endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")

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


# ==============================================================
# 🔹 CREATE - Create a new role
# ==============================================================
@roles_and_permissions_router.post("/", response_model=RoleResponse)
async def create_new_role(payload: RoleCreate, db: AsyncSession = Depends(get_db),
                          _ok: bool = Depends(ensure_not_basic_user),
                          user_perms: dict = Depends(get_user_permissions)):
    # Require ADMIN_CREATION:READ permission to access roles endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")
    role_obj = await svc_create_role(db, payload)
    # Invalidate roles cache after creation
    await invalidate_pattern("roles:*")
    schema_data = RoleResponse.model_validate(role_obj)
    # audit role creation
    try:
        new_val = schema_data.model_dump()
        entity_id = f"role:{getattr(role_obj, 'role_id', None)}"
        await log_audit(entity="role", entity_id=entity_id, action="INSERT", new_value=new_val)
    except Exception:
        pass
    return schema_data.model_copy(update={"message": "Role created successfully"})


# ==============================================================
# 🔹 READ - Fetch list of all roles
# ==============================================================
@roles_and_permissions_router.get("/", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db), _ok: bool = Depends(ensure_not_basic_user), user_perms: dict = Depends(get_user_permissions)):
    # Require ADMIN_CREATION:READ permission to access roles endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")
    cache_key = "roles:all"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    roles = await svc_list_roles(db)
    result = [RoleResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in roles]
    await set_cached(cache_key, result, ttl=300)
    return result
