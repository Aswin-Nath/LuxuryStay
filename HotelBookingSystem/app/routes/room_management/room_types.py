from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.orm.rooms import RoomTypes
from app.models.postgres.room import RoomTypeCreate, RoomTypeResponse
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user

router = APIRouter(prefix="/api/room-types", tags=["ROOM_TYPES"])


@router.post("/", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    # unique type_name enforced by DB
    q = await db.execute(select(RoomTypes).where(RoomTypes.type_name == payload.type_name))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type already exists")

    obj = RoomTypes(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Room type created"})


@router.get("/", response_model=List[RoomTypeResponse])
async def list_room_types(include_deleted: Optional[bool] = Query(False), db: AsyncSession = Depends(get_db)):
    stmt = select(RoomTypes)
    if not include_deleted:
        stmt = stmt.where(RoomTypes.is_deleted == False)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [RoomTypeResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in items]


@router.get("/{room_type_id}", response_model=RoomTypeResponse)
async def get_room_type(room_type_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return RoomTypeResponse.model_validate(obj)


@router.put("/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(room_type_id: int, payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    await db.execute(
        update(RoomTypes)
        .where(RoomTypes.room_type_id == room_type_id)
        .values(**payload.model_dump())
    )
    await db.commit()
    # refresh
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.delete("/{room_type_id}")
async def soft_delete_room_type(room_type_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    # soft delete
    await db.execute(update(RoomTypes).where(RoomTypes.room_type_id == room_type_id).values(is_deleted=True))
    await db.commit()
    return {"message": "Room type soft-deleted"}
