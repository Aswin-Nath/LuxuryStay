from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.rooms import RoomAmenityMap, Rooms, RoomAmenities


async def map_amenity(db: AsyncSession, payload) -> None:
    r = await db.execute(select(Rooms).where(Rooms.room_id == payload.room_id))
    room = r.scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    a = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == payload.amenity_id))
    amen = a.scalars().first()
    if not amen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")

    existing = await db.execute(
        select(RoomAmenityMap).where(
            RoomAmenityMap.room_id == payload.room_id,
            RoomAmenityMap.amenity_id == payload.amenity_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mapping already exists")

    obj = RoomAmenityMap(**payload.model_dump())
    db.add(obj)
    await db.commit()
    return


async def get_amenities_for_room(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
    res = await db.execute(
        select(RoomAmenities)
        .join(RoomAmenityMap, RoomAmenityMap.amenity_id == RoomAmenities.amenity_id)
        .where(RoomAmenityMap.room_id == room_id)
    )
    items = res.scalars().all()
    return items


async def unmap_amenity(db: AsyncSession, room_id: int, amenity_id: int) -> None:
    res = await db.execute(
        select(RoomAmenityMap).where(
            RoomAmenityMap.room_id == room_id,
            RoomAmenityMap.amenity_id == amenity_id,
        )
    )
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    await db.delete(obj)
    await db.commit()
