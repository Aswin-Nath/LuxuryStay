from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status


from app.models.sqlalchemy_schemas.roles import Roles
from app.models.sqlalchemy_schemas.permissions import Permissions, PermissionRoleMap, Resources


async def assign_permissions_to_role(db: AsyncSession, role_id: int, permission_ids: List[int]):
    # Verify role exists
    result = await db.execute(select(Roles).where(Roles.role_id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role ID {role_id} not found.")

    # Assign permissions
    for pid in permission_ids:
        exists = await db.execute(
            select(PermissionRoleMap)
            .where(PermissionRoleMap.role_id == role_id)
            .where(PermissionRoleMap.permission_id == pid)
        )
        if not exists.scalars().first():
            db.add(PermissionRoleMap(role_id=role_id, permission_id=pid))

    await db.commit()
    return {
        "role_id": role_id,
        "assigned_permission_ids": permission_ids,
        "message": "Permissions assigned successfully",
    }


async def get_permissions_by_role(db: AsyncSession, role_id: int):
    result = await db.execute(
        select(Permissions)
        .join(PermissionRoleMap, Permissions.permission_id == PermissionRoleMap.permission_id)
        .where(PermissionRoleMap.role_id == role_id)
    )
    permissions = result.scalars().all()
    if not permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No permissions found for role_id {role_id}")
    return permissions


async def get_permissions_by_resources(db: AsyncSession, resources: List[str]):
    valid_resources = []
    for r in resources:
        try:
            valid_resources.append(Resources(r.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid resource '{r}'")

    result = await db.execute(select(Permissions).where(Permissions.resource.in_(valid_resources)))
    permissions = result.scalars().all()
    return permissions


async def get_roles_for_permission(db: AsyncSession, permission_id: int):
    result = await db.execute(
        select(Roles)
        .join(PermissionRoleMap, Roles.role_id == PermissionRoleMap.role_id)
        .where(PermissionRoleMap.permission_id == permission_id)
    )
    roles = result.scalars().all()
    if not roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No roles found for permission_id {permission_id}")
    return roles



async def create_role(db: AsyncSession, payload) -> Roles:
    result = await db.execute(select(Roles).where(Roles.role_name == payload.role_name))
    existing_role = result.scalars().first()

    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role '{payload.role_name}' already exists.")

    role_obj = Roles(**payload.model_dump())
    db.add(role_obj)
    await db.commit()
    await db.refresh(role_obj)
    return role_obj


async def list_roles(db: AsyncSession) -> List[Roles]:
    result = await db.execute(select(Roles))
    roles = result.scalars().all()
    return roles
