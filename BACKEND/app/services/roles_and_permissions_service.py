from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.roles_and_permissions import (
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
	"""
	Assign permissions to a role.
	
	Creates permission-role associations for a specific role. Skips permissions already
	assigned to the role. Useful for role management and access control configuration.
	
	Args:
		db (AsyncSession): Database session for executing queries.
		role_id (int): The ID of the role to assign permissions to.
		permission_ids (List[int]): List of permission IDs to assign.
	
	Returns:
		dict: Confirmation with role_id, assigned permission IDs, and success message.
	
	Raises:
		HTTPException (404): If role_id not found.
	"""
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
	"""
	Retrieve all permissions assigned to a role.
	
	Fetches the complete set of permissions for a specific role. Returns all granular
	permissions that users with this role possess (e.g., WRITE on BOOKING, READ on ROOM).
	
	Args:
		db (AsyncSession): Database session for executing the query.
		role_id (int): The ID of the role.
	
	Returns:
		list: Permission records assigned to the role.
	
	Raises:
		HTTPException (404): If no permissions found for role_id.
	"""
	permissions_list = await fetch_permissions_by_role_id(db, role_id)
	if not permissions_list:
		raise HTTPException(status_code=404, detail=f"No permissions found for role_id {role_id}")
	return permissions_list


# ==========================================================
# 🔹 PERMISSIONS BY RESOURCE
# ==========================================================
async def get_permissions_by_resources(db: AsyncSession, resources: List[str]):
	"""
	Retrieve permissions for specific resources.
	
	Queries permissions available for one or more resources (e.g., BOOKING, ROOM_MANAGEMENT).
	Validates that resources are valid enum values and returns all permissions linked to them.
	
	Args:
		db (AsyncSession): Database session for executing the query.
	
	Returns:
		list: Permission records for the specified resources.
	
	Raises:
		HTTPException (400): If any resource name is invalid.
	"""
	valid_resources = []
	for resource in resources:
		try:
			valid_resources.append(resource.upper())
		except ValueError:
			raise HTTPException(status_code=400, detail=f"Invalid resource '{resource}'")

	permissions_list = await fetch_permissions_by_resources(db, valid_resources)
	return permissions_list


# ==========================================================
# 🔹 ROLES BY PERMISSION
# ==========================================================
async def get_roles_for_permission(db: AsyncSession, permission_id: int):
	"""
	Retrieve all roles that have a specific permission.
	
	Queries which roles are granted a particular permission. Useful for permission-centric
	access control queries and role hierarchy analysis.
	
	Args:
		db (AsyncSession): Database session for executing the query.
		permission_id (int): The ID of the permission.
	
	Returns:
		list: Role records that have the specified permission.
	
	Raises:
		HTTPException (404): If no roles found for permission_id.
	"""
	roles_list = await fetch_roles_by_permission_id(db, permission_id)
	if not roles_list:
		raise HTTPException(status_code=404, detail=f"No roles found for permission_id {permission_id}")
	return roles_list


# ==========================================================
# 🔹 CREATE ROLE
# ==========================================================
async def create_role(db: AsyncSession, payload) -> Roles:
	"""
	Create a new system role.
	
	Creates a new role with the specified name and description. Enforces uniqueness of role
	names to prevent duplicates. New roles start without permissions and must have them
	assigned separately using assign_permissions_to_role().
	
	Args:
		db (AsyncSession): Database session for executing queries.
		payload: Pydantic model containing role_name, description, and other role details.
	
	Returns:
		Roles: The newly created role record with role_id and timestamps.
	
	Raises:
		HTTPException (409): If role_name already exists.
	"""
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
	"""
	Retrieve all system roles.
	
	Fetches complete list of all roles configured in the system. Each role defines a
	set of permissions that can be assigned to users. Used for role selection in user
	management and permission administration interfaces.
	
	Args:
		db (AsyncSession): Database session for executing the query.
	
	Returns:
		List[Roles]: All role records in the system.
	"""
	return await fetch_all_roles(db)
