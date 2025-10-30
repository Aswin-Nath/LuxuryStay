from fastapi import APIRouter, Depends, HTTPException, status,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database.postgres_connection import get_db
from app.models.orm.permissions import Permissions, Resources, PermissionTypes,PermissionRoleMap
from app.dependencies.authentication import ensure_not_basic_user
from app.models.orm.roles import Roles
from app.models.postgres.permissions import PermissionCreate, PermissionResponse,RolePermissionAssign,RolePermissionResponse
from sqlalchemy.exc import IntegrityError

permissions_router = APIRouter(prefix="/permissions", tags=["PERMISSIONS"], dependencies=[Depends(ensure_not_basic_user)])


# ==============================================================
# 1️⃣ CREATE PERMISSIONS
# ==============================================================
@permissions_router.post("/", response_model=List[PermissionResponse])
async def create_permissions(payload: List[PermissionCreate], db: AsyncSession = Depends(get_db)):
    created_permissions = []

    for p in payload:
        # Validate and normalize Enums
        try:
            resource_enum = Resources(p.resource.upper())
            permission_enum = PermissionTypes(p.permission_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource '{p.resource}' or permission_type '{p.permission_type}'. "
                       f"Allowed values: {', '.join([r.value for r in Resources])} / "
                       f"{', '.join([pt.value for pt in PermissionTypes])}"
            )
        
        # Check for existing
        existing = await db.execute(
            select(Permissions).where(
                (Permissions.resource == resource_enum) &
                (Permissions.permission_type == permission_enum)
            )
        )
        if existing.scalars().first():
            continue

        # Attempt insert
        new_perm = Permissions(resource=resource_enum, permission_type=permission_enum)
        db.add(new_perm)
        try:
            await db.flush()
            await db.refresh(new_perm)
        except IntegrityError:
            await db.rollback()
            continue  # Duplicate constraint safety

        created_permissions.append(
            PermissionResponse.model_validate(new_perm).model_copy(
                update={"message": "Permission created successfully"}
            )
        )

    await db.commit()
    return created_permissions


# ==============================================================
# 2️⃣ ASSIGN PERMISSIONS TO A ROLE
# ==============================================================
@permissions_router.post("/assign", response_model=RolePermissionResponse)
async def assign_permissions_to_role(payload: RolePermissionAssign, db: AsyncSession = Depends(get_db)):
    # Verify role exists
    role_check = await db.execute(select(Roles).where(Roles.role_id == payload.role_id))
    role = role_check.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role ID {payload.role_id} not found."
        )

    # Assign permissions
    for pid in payload.permission_ids:
        exists = await db.execute(
            select(PermissionRoleMap)
            .where(PermissionRoleMap.role_id == payload.role_id)
            .where(PermissionRoleMap.permission_id == pid)
        )
        if not exists.scalars().first():
            db.add(PermissionRoleMap(role_id=payload.role_id, permission_id=pid))

    await db.commit()

    return RolePermissionResponse(
        role_id=payload.role_id,
        assigned_permission_ids=payload.permission_ids,
        message="Permissions assigned successfully"
    )


# ==============================================================
# 3️⃣ GET PERMISSIONS BY ROLE_ID
# ==============================================================
@permissions_router.get("/by-role/{role_id}", response_model=List[PermissionResponse])
async def get_permissions_by_role(role_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Permissions)
        .join(PermissionRoleMap, Permissions.permission_id == PermissionRoleMap.permission_id)
        .where(PermissionRoleMap.role_id == role_id)
    )
    permissions = result.scalars().all()

    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No permissions found for role_id {role_id}"
        )

    return [
        PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"})
        for p in permissions
    ]


# ==============================================================
# 4️⃣ GET PERMISSIONS BY MULTIPLE RESOURCES
# ==============================================================
@permissions_router.get("/by-resources", response_model=List[PermissionResponse])
async def get_permissions_by_resources(
    resources: List[str] = Query(..., description="List of resources to filter by"),
    db: AsyncSession = Depends(get_db)
):
    # Normalize and validate Enums
    valid_resources = []
    for r in resources:
        try:
            valid_resources.append(Resources(r.upper()))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource '{r}'. Allowed: {', '.join([res.value for res in Resources])}"
            )

    result = await db.execute(select(Permissions).where(Permissions.resource.in_(valid_resources)))
    permissions = result.scalars().all()

    return [
        PermissionResponse.model_validate(p).model_copy(update={"message": "Fetched successfully"})
        for p in permissions
    ]


# ==============================================================
# 5️⃣ GET ROLES ASSIGNED TO A PERMISSION
# ==============================================================
@permissions_router.get("/{permission_id}/roles")
async def get_roles_for_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Roles)
        .join(PermissionRoleMap, Roles.role_id == PermissionRoleMap.role_id)
        .where(PermissionRoleMap.permission_id == permission_id)
    )
    roles = result.scalars().all()

    if not roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No roles found for permission_id {permission_id}"
        )

    return {
        "permission_id": permission_id,
        "roles": [{"role_id": r.role_id, "role_name": r.role_name} for r in roles],
        "message": "Roles fetched successfully"
    }