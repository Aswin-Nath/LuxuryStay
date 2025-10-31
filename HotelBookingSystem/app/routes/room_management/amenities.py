from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.rooms import RoomAmenities
from app.models.pydantic_models.room import AmenityCreate, AmenityResponse, Amenity
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user
from app.services.room_management.amenities_service import (
    create_amenity as svc_create_amenity,
    list_amenities as svc_list_amenities,
    get_amenity as svc_get_amenity,
    delete_amenity as svc_delete_amenity,
)

router = APIRouter(prefix="/api/amenities", tags=["AMENITIES"])


@router.post("/", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(payload: AmenityCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    obj = await svc_create_amenity(db, payload)
    return AmenityResponse.model_validate(obj).model_copy(update={"message": "Amenity created"})


@router.get("/", response_model=List[Amenity])
async def list_amenities(db: AsyncSession = Depends(get_db)):
    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


@router.get("/{amenity_id}", response_model=AmenityResponse)
async def get_amenity(amenity_id: int, db: AsyncSession = Depends(get_db)):
    obj = await svc_get_amenity(db, amenity_id)
    return AmenityResponse.model_validate(obj)


@router.delete("/{amenity_id}")
async def delete_amenity(amenity_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    await svc_delete_amenity(db, amenity_id)
    return {"message": "Amenity deleted"}
