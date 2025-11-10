from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.roles import Roles
from app.models.sqlalchemy_schemas.permissions import Permissions, PermissionRoleMap


# ==========================================================
# 🔹 ROLE CRUD
# ==========================================================
async def insert_role_record(db: AsyncSession, data: dict) -> Roles:
	role_record = Roles(**data)
	db.add(role_record)
	await db.flush()
	return role_record


async def fetch_all_roles(db: AsyncSession) -> List[Roles]:
	query_result = await db.execute(select(Roles))
	return query_result.scalars().all()


async def fetch_role_by_id(db: AsyncSession, role_id: int) -> Optional[Roles]:
	query_result = await db.execute(select(Roles).where(Roles.role_id == role_id))
	return query_result.scalars().first()


async def fetch_role_by_name(db: AsyncSession, role_name: str) -> Optional[Roles]:
	query_result = await db.execute(select(Roles).where(Roles.role_name == role_name))
	return query_result.scalars().first()


# ==========================================================
# 🔹 PERMISSIONS CRUD
# ==========================================================
async def fetch_permissions_by_role_id(db: AsyncSession, role_id: int) -> List[Permissions]:
	query_result = await db.execute(
		select(Permissions)
		.join(PermissionRoleMap, Permissions.permission_id == PermissionRoleMap.permission_id)
		.where(PermissionRoleMap.role_id == role_id)
	)
	return query_result.scalars().all()


async def fetch_permissions_by_resources(db: AsyncSession, resources) -> List[Permissions]:
	query_result = await db.execute(select(Permissions).where(Permissions.resource.in_(resources)))
	return query_result.scalars().all()


async def fetch_roles_by_permission_id(db: AsyncSession, permission_id: int) -> List[Roles]:
	query_result = await db.execute(
		select(Roles)
		.join(PermissionRoleMap, Roles.role_id == PermissionRoleMap.role_id)
		.where(PermissionRoleMap.permission_id == permission_id)
	)
	return query_result.scalars().all()


async def fetch_permission_role_map(db: AsyncSession, role_id: int, permission_id: int) -> Optional[PermissionRoleMap]:
	query_result = await db.execute(
		select(PermissionRoleMap)
		.where(PermissionRoleMap.role_id == role_id)
		.where(PermissionRoleMap.permission_id == permission_id)
	)
	return query_result.scalars().first()


async def insert_permission_role_map(db: AsyncSession, role_id: int, permission_id: int) -> PermissionRoleMap:
	permission_role_map_record = PermissionRoleMap(role_id=role_id, permission_id=permission_id)
	db.add(permission_role_map_record)
	await db.flush()
	return permission_role_map_record
