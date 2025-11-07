from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.roles import Roles
from app.models.sqlalchemy_schemas.permissions import Permissions, PermissionRoleMap, Resources


# ==========================================================
# 🔹 ROLE CRUD
# ==========================================================
async def insert_role_record(db: AsyncSession, data: dict) -> Roles:
	obj = Roles(**data)
	db.add(obj)
	await db.flush()
	return obj


async def fetch_all_roles(db: AsyncSession) -> List[Roles]:
	res = await db.execute(select(Roles))
	return res.scalars().all()


async def fetch_role_by_id(db: AsyncSession, role_id: int) -> Optional[Roles]:
	res = await db.execute(select(Roles).where(Roles.role_id == role_id))
	return res.scalars().first()


async def fetch_role_by_name(db: AsyncSession, role_name: str) -> Optional[Roles]:
	res = await db.execute(select(Roles).where(Roles.role_name == role_name))
	return res.scalars().first()


# ==========================================================
# 🔹 PERMISSIONS CRUD
# ==========================================================
async def fetch_permissions_by_role_id(db: AsyncSession, role_id: int) -> List[Permissions]:
	res = await db.execute(
		select(Permissions)
		.join(PermissionRoleMap, Permissions.permission_id == PermissionRoleMap.permission_id)
		.where(PermissionRoleMap.role_id == role_id)
	)
	return res.scalars().all()


async def fetch_permissions_by_resources(db: AsyncSession, resources: List[Resources]) -> List[Permissions]:
	res = await db.execute(select(Permissions).where(Permissions.resource.in_(resources)))
	return res.scalars().all()


async def fetch_roles_by_permission_id(db: AsyncSession, permission_id: int) -> List[Roles]:
	res = await db.execute(
		select(Roles)
		.join(PermissionRoleMap, Roles.role_id == PermissionRoleMap.role_id)
		.where(PermissionRoleMap.permission_id == permission_id)
	)
	return res.scalars().all()


async def fetch_permission_role_map(db: AsyncSession, role_id: int, permission_id: int) -> Optional[PermissionRoleMap]:
	res = await db.execute(
		select(PermissionRoleMap)
		.where(PermissionRoleMap.role_id == role_id)
		.where(PermissionRoleMap.permission_id == permission_id)
	)
	return res.scalars().first()


async def insert_permission_role_map(db: AsyncSession, role_id: int, permission_id: int) -> PermissionRoleMap:
	obj = PermissionRoleMap(role_id=role_id, permission_id=permission_id)
	db.add(obj)
	await db.flush()
	return obj
