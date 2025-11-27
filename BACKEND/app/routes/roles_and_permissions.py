from fastapi import APIRouter, Depends, Query, HTTPException, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.permissions import PermissionResponse, RolePermissionAssign, RolePermissionResponse
from app.schemas.pydantic_models.roles import RoleCreate, RoleResponse
from app.models.sqlalchemy_schemas.permissions import Permissions, PermissionRoleMap
from app.models.sqlalchemy_schemas.roles import Roles
from app.services.roles_and_permissions_service import (
    assign_permissions_to_role as svc_assign_permissions_to_role,
    get_permissions_by_role as svc_get_permissions_by_role,
    get_permissions_by_resources as svc_get_permissions_by_resources,
    get_roles_for_permission as svc_get_roles_for_permission,
    create_role as svc_create_role, list_roles as svc_list_roles
)
from app.dependencies.authentication import check_permission, get_current_user
from app.utils.authentication_util import invalidate_permissions_cache
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_util import log_audit
from app.models.sqlalchemy_schemas.users import Users


# Single combined router
roles_and_permissions_router = APIRouter(prefix="/roles", tags=["ROLES"])


# ==============================================================
# 🔹 READ - Get current user's role and permissions
# ==============================================================
@roles_and_permissions_router.get("/me")
async def get_current_user_permissions(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve current user's role and all assigned permissions.
    
    Endpoint to fetch the currently authenticated user's role information and all permissions
    assigned to their role. This is useful for UI to determine which features/actions the user
    can access. Results are cached based on the user's role_id for 300 seconds.
    
    **Authorization:** Requires valid authentication token (any authenticated user).
    
    Args:
        current_user (Users): Currently authenticated user from get_current_user dependency.
        db (AsyncSession): Database session dependency.
    
    Returns:
        dict: Contains user_id, role info (role_id, role_name), and list of permission names.
            Example:
            {
                "user_id": 1,
                "role_id": 2,
                "role_name": "super_admin",
                "permissions": [
                    "ADMIN_CREATION:READ",
                    "ADMIN_CREATION:WRITE",
                    "ROOM_MANAGEMENT:WRITE"
                ],
                "message": "User permissions fetched successfully"
            }
    
    Raises:
        HTTPException (401): If token is invalid or user not found.
        HTTPException (404): If user's role not found (data integrity issue).
    """
    try:
        # Fetch user's role
        role_result = await db.execute(
            select(Roles).where(Roles.role_id == current_user.role_id)
        )
        role = role_result.scalars().first()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User's role not found"
            )
        
        # Try to get permissions from cache
        cache_key = f"user_perms:{current_user.role_id}"
        cached_permissions = await get_cached(cache_key)
        
        if cached_permissions is not None:
            permissions = cached_permissions
        else:
            # Query permissions from database
            perms_result = await db.execute(
                select(Permissions.permission_name)
                .join(PermissionRoleMap, PermissionRoleMap.permission_id == Permissions.permission_id)
                .where(PermissionRoleMap.role_id == current_user.role_id)
            )
            
            # Flatten tuple results like [('X',), ('Y',)] → ['X', 'Y']
            permissions = [perm[0] for perm in perms_result.all()]
            
            # Cache permissions for this role with 300-second TTL
            await set_cached(cache_key, permissions, ttl=300)
        
        return {
            "role_id": current_user.role_id,
            "permissions": permissions,
            "message": "User permissions fetched successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user permissions"
        )


# ==============================================================
# 🔹 CREATE - Assign permissions to a role
# ==============================================================
@roles_and_permissions_router.post("/assign", response_model=RolePermissionResponse)
async def assign_permissions_to_role(
    payload: RolePermissionAssign,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Assign permissions to a role.
    
    Endpoint to associate one or more permissions with a specific role. Permissions already
    linked to the role are skipped. Used for role configuration and access control setup.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        payload (RolePermissionAssign): Request body containing role_id and list of permission_ids.
        db (AsyncSession): Database session dependency.
        token_payload (dict): Token validation with ADMIN_CREATION:WRITE scope requirement.
    
    Returns:
        RolePermissionResponse: Confirmation with role_id, assigned permission IDs, and success message.
    
    Raises:
        HTTPException (403): If user lacks ADMIN_CREATION:WRITE permission.
        HTTPException (404): If role_id not found (from service).
        HTTPException (409): If permission assignment conflicts (from service).
    """
    assignment_result = await svc_assign_permissions_to_role(db, payload.role_id, payload.permission_ids)
    
    # Invalidate permissions cache for this role (permissions changed)
    await invalidate_permissions_cache(payload.role_id)
    
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
@roles_and_permissions_router.get("/permissions")
async def get_permissions(
    permission_id: int | None = Query(None, description="Permission id to fetch roles for"),
    role_id: int | None = Query(None, description="Role id to fetch permissions for"),
    resources: List[str] | None = Query(None, description="List of resources to filter by"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:READ"]),
):
    """
    Retrieve permissions by role, resource, or find roles for a permission.
    
    Flexible endpoint supporting three query modes (provide exactly one):
    - Query by role_id: Returns all permissions assigned to a specific role.
    - Query by resources: Returns permissions available for specified resources (e.g., BOOKING, ROOM_MANAGEMENT).
    - Query by permission_id: Returns all roles that have a specific permission.
    
    **Authorization:** Requires ADMIN_CREATION:READ permission.
    
    Args:
        permission_id (int | None): Query parameter - permission ID to find roles for.
        role_id (int | None): Query parameter - role ID to find permissions for.
        resources (List[str] | None): Query parameter - list of resource names to filter permissions.
        db (AsyncSession): Database session dependency.
        token_payload (dict): Token validation with ADMIN_CREATION:READ scope requirement.
    
    Returns:
        dict or List: 
            - If permission_id: dict with permission_id, list of roles, and success message.
            - If role_id: list of PermissionResponse objects for the role.
            - If resources: list of PermissionResponse objects for the resources.
    
    Raises:
        HTTPException (400): If no query parameter provided or multiple provided.
        HTTPException (403): If user lacks ADMIN_CREATION:READ permission.
        HTTPException (404): If no permissions/roles found (from service).
    """
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


# ==============================================================
# 🔹 CREATE - Create a new role
# ==============================================================
@roles_and_permissions_router.post("/", response_model=RoleResponse)
async def create_new_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Create a new system role.
    
    Endpoint to define a new role in the system. Role names must be unique. Newly created
    roles start without permissions and must be populated using the /assign endpoint.
    Cache is invalidated after successful creation to reflect changes system-wide.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        payload (RoleCreate): Request body containing role_name, description, and role details.
        db (AsyncSession): Database session dependency.
        token_payload (dict): Token validation with ADMIN_CREATION:WRITE scope requirement.
    
    Returns:
        RoleResponse: The newly created role record with role_id, timestamps, and success message.
    
    Raises:
        HTTPException (403): If user lacks ADMIN_CREATION:WRITE permission.
        HTTPException (409): If role_name already exists (from service).
    
    Side Effects:
        - Invalidates roles cache pattern ("roles:*") to ensure consistency.
        - Creates audit log entry for role creation.
    """
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
async def list_roles(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:READ"]),
):
    """
    Retrieve all system roles.
    
    Endpoint to fetch the complete list of all roles configured in the system. Results are
    cached for 300 seconds (5 minutes) to reduce database load. Each role record includes
    role_id, role_name, description, and timestamps. Used for role selection in user
    management interfaces and permission administration.
    
    **Authorization:** Requires ADMIN_CREATION:READ permission.
    
    Args:
        db (AsyncSession): Database session dependency.
        token_payload (dict): Token validation with ADMIN_CREATION:READ scope requirement.
    
    Returns:
        List[RoleResponse]: List of all role records with success message and cache status.
    
    Raises:
        HTTPException (403): If user lacks ADMIN_CREATION:READ permission.
    
    Side Effects:
        - Uses Redis cache with key "roles:all" and TTL of 300 seconds.
        - Returns cached results if available, otherwise queries database and caches result.
    """
    cache_key = "roles:all"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    roles = await svc_list_roles(db)
    result = [RoleResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in roles]
    await set_cached(cache_key, result, ttl=300)
    return result
