from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.rooms import RoomAmenities


async def create_amenity(db: AsyncSession, payload) -> RoomAmenities:
    q = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_name == payload.amenity_name))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Amenity already exists")
    obj = RoomAmenities(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_amenities(db: AsyncSession) -> List[RoomAmenities]:
    res = await db.execute(select(RoomAmenities))
    items = res.scalars().all()
    return items


async def get_amenity(db: AsyncSession, amenity_id: int) -> RoomAmenities:
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")
    return obj


async def delete_amenity(db: AsyncSession, amenity_id: int) -> None:
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")
    if obj.rooms:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amenity is mapped to rooms; unmap first")
    await db.delete(obj)
    await db.commit()
