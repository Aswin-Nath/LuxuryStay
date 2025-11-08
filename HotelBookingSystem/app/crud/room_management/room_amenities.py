from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.rooms import RoomAmenityMap, Rooms, RoomAmenities


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_room_amenity_map(db: AsyncSession, data: dict) -> RoomAmenityMap:
	obj = RoomAmenityMap(**data)
	db.add(obj)
	await db.flush()
	return obj


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
	res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
	return res.scalars().first()


async def fetch_amenity_by_id(db: AsyncSession, amenity_id: int) -> Optional[RoomAmenities]:
	res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
	return res.scalars().first()


async def fetch_mapping_exists(db: AsyncSession, room_id: int, amenity_id: int) -> Optional[RoomAmenityMap]:
	res = await db.execute(
		select(RoomAmenityMap)
		.where(RoomAmenityMap.room_id == room_id)
		.where(RoomAmenityMap.amenity_id == amenity_id)
	)
	return res.scalars().first()


async def fetch_amenities_by_room_id(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
	res = await db.execute(
		select(RoomAmenities)
		.join(RoomAmenityMap, RoomAmenityMap.amenity_id == RoomAmenities.amenity_id)
		.where(RoomAmenityMap.room_id == room_id)
	)
	return res.scalars().all()


async def fetch_rooms_by_amenity_id(db: AsyncSession, amenity_id: int) -> List[Rooms]:
	res = await db.execute(
		select(Rooms)
		.join(RoomAmenityMap, RoomAmenityMap.room_id == Rooms.room_id)
		.where(RoomAmenityMap.amenity_id == amenity_id)
	)
	return res.scalars().all()


async def fetch_mapping_by_ids(db: AsyncSession, room_id: int, amenity_id: int) -> Optional[RoomAmenityMap]:
	res = await db.execute(
		select(RoomAmenityMap)
		.where(RoomAmenityMap.room_id == room_id)
		.where(RoomAmenityMap.amenity_id == amenity_id)
	)
	return res.scalars().first()


# ==========================================================
# 🔹 DELETE
# ==========================================================
async def delete_room_amenity_map(db: AsyncSession, obj: RoomAmenityMap) -> None:
	await db.delete(obj)
	await db.flush()
