from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.rooms import Rooms, RoomAmenities
from app.crud.room_management.room_amenities import (
	fetch_room_by_id,
	fetch_amenity_by_id,
	fetch_mapping_exists,
	insert_room_amenity_map,
	fetch_amenities_by_room_id,
	fetch_rooms_by_amenity_id,
	fetch_mapping_by_ids,
	delete_room_amenity_map,
)


# ==========================================================
# 🔹 MAP AMENITY TO ROOM
# ==========================================================
async def map_amenity(db: AsyncSession, payload) -> None:
	room = await fetch_room_by_id(db, payload.room_id)
	if not room:
		raise HTTPException(status_code=404, detail="Room not found")

	amen = await fetch_amenity_by_id(db, payload.amenity_id)
	if not amen:
		raise HTTPException(status_code=404, detail="Amenity not found")

	existing = await fetch_mapping_exists(db, payload.room_id, payload.amenity_id)
	if existing:
		raise HTTPException(status_code=409, detail="Mapping already exists")

	obj = await insert_room_amenity_map(db, payload.model_dump())
	await db.commit()
	return obj


# ==========================================================
# 🔹 GET AMENITIES FOR A ROOM
# ==========================================================
async def get_amenities_for_room(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
	return await fetch_amenities_by_room_id(db, room_id)


# ==========================================================
# 🔹 GET ROOMS FOR AN AMENITY
# ==========================================================
async def get_rooms_for_amenity(db: AsyncSession, amenity_id: int) -> List[Rooms]:
	return await fetch_rooms_by_amenity_id(db, amenity_id)


# ==========================================================
# 🔹 UNMAP AMENITY FROM ROOM
# ==========================================================
async def unmap_amenity(db: AsyncSession, room_id: int, amenity_id: int) -> None:
	obj = await fetch_mapping_by_ids(db, room_id, amenity_id)
	if not obj:
		raise HTTPException(status_code=404, detail="Mapping not found")

	await delete_room_amenity_map(db, obj)
	await db.commit()
