from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.rooms import RoomTypes


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_room_type(db: AsyncSession, data: dict) -> RoomTypes:
	obj = RoomTypes(**data)
	db.add(obj)
	await db.flush()
	return obj


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_room_type_by_id(db: AsyncSession, room_type_id: int) -> Optional[RoomTypes]:
	res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
	return res.scalars().first()


async def fetch_room_type_by_name(db: AsyncSession, type_name: str) -> Optional[RoomTypes]:
	res = await db.execute(select(RoomTypes).where(RoomTypes.type_name == type_name))
	return res.scalars().first()


async def fetch_all_room_types(db: AsyncSession, include_deleted: bool = False) -> List[RoomTypes]:
	stmt = select(RoomTypes)
	if not include_deleted:
		stmt = stmt.where(RoomTypes.is_deleted == False)
	res = await db.execute(stmt)
	return res.scalars().all()


# ==========================================================
# 🔹 UPDATE
# ==========================================================
async def update_room_type_by_id(db: AsyncSession, room_type_id: int, updates: dict) -> None:
	if updates:
		await db.execute(
			update(RoomTypes)
			.where(RoomTypes.room_type_id == room_type_id)
			.values(**updates)
		)
	await db.flush()


# ==========================================================
# 🔹 SOFT DELETE
# ==========================================================
async def mark_room_type_deleted(db: AsyncSession, room_type_id: int) -> None:
	await db.execute(
		update(RoomTypes)
		.where(RoomTypes.room_type_id == room_type_id)
		.values(is_deleted=True)
	)
	await db.flush()
