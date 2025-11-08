from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.rooms import RoomAmenities


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_amenity(db: AsyncSession, data: dict) -> RoomAmenities:
	obj = RoomAmenities(**data)
	db.add(obj)
	await db.flush()
	return obj


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_all_amenities(db: AsyncSession) -> List[RoomAmenities]:
	res = await db.execute(select(RoomAmenities))
	return res.scalars().all()


async def fetch_amenity_by_id(db: AsyncSession, amenity_id: int) -> Optional[RoomAmenities]:
	res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
	return res.scalars().first()


async def fetch_amenity_by_name(db: AsyncSession, amenity_name: str) -> Optional[RoomAmenities]:
	res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_name == amenity_name))
	return res.scalars().first()


# ==========================================================
# 🔹 DELETE
# ==========================================================
async def remove_amenity(db: AsyncSession, amenity: RoomAmenities) -> None:
	await db.delete(amenity)
	await db.flush()
