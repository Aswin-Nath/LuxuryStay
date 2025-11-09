from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.permissions import Resources
from app.crud.roles_and_permissions_management.roles_and_permissions import (
	fetch_role_by_id,
	fetch_role_by_name,
	fetch_all_roles,
	insert_role_record,
	fetch_permissions_by_role_id,
	fetch_permissions_by_resources,
	fetch_roles_by_permission_id,
	fetch_permission_role_map,
	insert_permission_role_map,
)
from app.models.sqlalchemy_schemas.roles import Roles


# ==========================================================
# 🔹 ASSIGN PERMISSIONS
# ==========================================================
async def assign_permissions_to_role(db: AsyncSession, role_id: int, permission_ids: List[int]):
	role = await fetch_role_by_id(db, role_id)
	if not role:
		raise HTTPException(status_code=404, detail=f"Role ID {role_id} not found.")

	for pid in permission_ids:
		existing = await fetch_permission_role_map(db, role_id, pid)
		if not existing:
			await insert_permission_role_map(db, role_id, pid)

	await db.commit()
	return {
		"role_id": role_id,
		"assigned_permission_ids": permission_ids,
		"message": "Permissions assigned successfully",
	}


# ==========================================================
# 🔹 PERMISSIONS BY ROLE
# ==========================================================
async def get_permissions_by_role(db: AsyncSession, role_id: int):
	permissions_list = await fetch_permissions_by_role_id(db, role_id)
	if not permissions_list:
		raise HTTPException(status_code=404, detail=f"No permissions found for role_id {role_id}")
	return permissions_list


# ==========================================================
# 🔹 PERMISSIONS BY RESOURCE
# ==========================================================
async def get_permissions_by_resources(db: AsyncSession, resources: List[str]):
	valid_resources = []
	for resource in resources:
		try:
			valid_resources.append(Resources(resource.upper()))
		except ValueError:
			raise HTTPException(status_code=400, detail=f"Invalid resource '{resource}'")

	permissions_list = await fetch_permissions_by_resources(db, valid_resources)
	return permissions_list


# ==========================================================
# 🔹 ROLES BY PERMISSION
# ==========================================================
async def get_roles_for_permission(db: AsyncSession, permission_id: int):
	roles_list = await fetch_roles_by_permission_id(db, permission_id)
	if not roles_list:
		raise HTTPException(status_code=404, detail=f"No roles found for permission_id {permission_id}")
	return roles_list


# ==========================================================
# 🔹 CREATE ROLE
# ==========================================================
async def create_role(db: AsyncSession, payload) -> Roles:
	existing_role = await fetch_role_by_name(db, payload.role_name)
	if existing_role:
		raise HTTPException(status_code=409, detail=f"Role '{payload.role_name}' already exists.")

	role_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
	role_record = await insert_role_record(db, role_data)
	await db.commit()
	await db.refresh(role_record)
	return role_record


# ==========================================================
# 🔹 LIST ROLES
# ==========================================================
async def list_roles(db: AsyncSession) -> List[Roles]:
	return await fetch_all_roles(db)
