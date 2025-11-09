from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.sqlalchemy_schemas.rooms import RoomAmenities, RoomAmenityMap
from app.crud.room_management.amenities import (
	insert_amenity,
	fetch_all_amenities,
	fetch_amenity_by_id,
	fetch_amenity_by_name,
	remove_amenity,
)


# ==========================================================
# 🔹 CREATE AMENITY
# ==========================================================
async def create_amenity(db: AsyncSession, payload) -> RoomAmenities:
	existing = await fetch_amenity_by_name(db, payload.amenity_name)
	if existing:
		raise HTTPException(status_code=409, detail="Amenity already exists")

	obj = await insert_amenity(db, payload.model_dump())
	await db.commit()
	await db.refresh(obj)
	return obj


# ==========================================================
# 🔹 LIST AMENITIES
# ==========================================================
async def list_amenities(db: AsyncSession) -> List[RoomAmenities]:
	return await fetch_all_amenities(db)


# ==========================================================
# 🔹 GET AMENITY
# ==========================================================
async def get_amenity(db: AsyncSession, amenity_id: int) -> RoomAmenities:
	obj = await fetch_amenity_by_id(db, amenity_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Amenity not found")
	return obj


# ==========================================================
# 🔹 DELETE AMENITY
# ==========================================================
async def delete_amenity(db: AsyncSession, amenity_id: int) -> None:
	obj = await fetch_amenity_by_id(db, amenity_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Amenity not found")

	# check if amenity is mapped to any rooms using a COUNT query
	count_result = await db.execute(
		select(func.count()).select_from(RoomAmenityMap).where(RoomAmenityMap.amenity_id == amenity_id)
	)
	count = count_result.scalar()
	if count > 0:
		raise HTTPException(status_code=400, detail="Amenity is mapped to rooms; unmap first")

	await remove_amenity(db, obj)
	await db.commit()
