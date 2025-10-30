from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.orm.rooms import RoomAmenityMap, Rooms, RoomAmenities
from app.models.postgres.room import RoomAmenityMapCreate, RoomAmenityMapResponse
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user

router = APIRouter(prefix="/api/room-amenities", tags=["ROOM_AMENITIES"])


@router.post("/", response_model=RoomAmenityMapResponse, status_code=status.HTTP_201_CREATED)
async def map_amenity(payload: RoomAmenityMapCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    # check room and amenity exist
    r = await db.execute(select(Rooms).where(Rooms.room_id == payload.room_id))
    room = r.scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    a = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == payload.amenity_id))
    amen = a.scalars().first()
    if not amen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")

    # prevent duplicates
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
    return RoomAmenityMapResponse.model_validate(payload).model_copy(update={"message": "Mapped successfully"})


@router.get("/room/{room_id}")
async def get_amenities_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(RoomAmenities)
        .join(RoomAmenityMap, RoomAmenityMap.amenity_id == RoomAmenities.amenity_id)
        .where(RoomAmenityMap.room_id == room_id)
    )
    items = res.scalars().all()
    return {"room_id": room_id, "amenities": [ {"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in items ]}


@router.delete("/")
async def unmap_amenity(room_id: int, amenity_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
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
    return {"message": "Unmapped successfully"}
