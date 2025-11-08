from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.rooms import RoomTypes
from app.crud.room_management.room_types import (
	insert_room_type,
	fetch_room_type_by_name,
	fetch_all_room_types,
	fetch_room_type_by_id,
	update_room_type_by_id,
	mark_room_type_deleted,
)


# ==========================================================
# 🔹 CREATE ROOM TYPE
# ==========================================================
async def create_room_type(db: AsyncSession, payload) -> RoomTypes:
	existing = await fetch_room_type_by_name(db, payload.type_name)
	if existing:
		raise HTTPException(status_code=409, detail="Room type already exists")

	obj = await insert_room_type(db, payload.model_dump())
	await db.commit()
	await db.refresh(obj)
	return obj


# ==========================================================
# 🔹 LIST ROOM TYPES
# ==========================================================
async def list_room_types(db: AsyncSession, include_deleted: Optional[bool] = False) -> List[RoomTypes]:
	return await fetch_all_room_types(db, include_deleted)


# ==========================================================
# 🔹 GET ROOM TYPE
# ==========================================================
async def get_room_type(db: AsyncSession, room_type_id: int) -> RoomTypes:
	obj = await fetch_room_type_by_id(db, room_type_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Room type not found")
	return obj


# ==========================================================
# 🔹 UPDATE ROOM TYPE
# ==========================================================
async def update_room_type(db: AsyncSession, room_type_id: int, payload) -> RoomTypes:
	obj = await fetch_room_type_by_id(db, room_type_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Room type not found")

	data = payload.model_dump(exclude_unset=True)
	await update_room_type_by_id(db, room_type_id, data)
	await db.commit()

	obj = await fetch_room_type_by_id(db, room_type_id)
	return obj


# ==========================================================
# 🔹 SOFT DELETE ROOM TYPE
# ==========================================================
async def soft_delete_room_type(db: AsyncSession, room_type_id: int) -> None:
	obj = await fetch_room_type_by_id(db, room_type_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Room type not found")

	await mark_room_type_deleted(db, room_type_id)
	await db.commit()
