from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.orm.rooms import RoomAmenities
from app.models.postgres.room import AmenityCreate, AmenityResponse, Amenity
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user

router = APIRouter(prefix="/api/amenities", tags=["AMENITIES"])


@router.post("/", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(payload: AmenityCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    q = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_name == payload.amenity_name))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Amenity already exists")
    obj = RoomAmenities(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return AmenityResponse.model_validate(obj).model_copy(update={"message": "Amenity created"})


@router.get("/", response_model=List[Amenity])
async def list_amenities(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RoomAmenities))
    items = res.scalars().all()
    return [Amenity.model_validate(a) for a in items]


@router.get("/{amenity_id}", response_model=AmenityResponse)
async def get_amenity(amenity_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")
    return AmenityResponse.model_validate(obj)


@router.delete("/{amenity_id}")
async def delete_amenity(amenity_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    # prevent delete if mapped
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found")
    # check mapping count by relying on relationship length (may require loading)
    if obj.rooms:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amenity is mapped to rooms; unmap first")
    await db.delete(obj)
    await db.commit()
    return {"message": "Amenity deleted"}
