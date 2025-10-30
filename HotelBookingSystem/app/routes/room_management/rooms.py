from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.orm.rooms import Rooms
from app.models.postgres.room import RoomCreate, RoomResponse, Room
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user

router = APIRouter(prefix="/api/rooms", tags=["ROOMS"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    # ensure room_no unique
    q = await db.execute(select(Rooms).where(Rooms.room_no == payload.room_no))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    obj = Rooms(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Room created"})


@router.get("/", response_model=List[Room])
async def list_rooms(
    room_type_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    is_freezed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Rooms)
    if room_type_id is not None:
        stmt = stmt.where(Rooms.room_type_id == room_type_id)
    if status_filter is not None:
        stmt = stmt.where(Rooms.room_status == status_filter)
    if is_freezed is not None:
        if is_freezed:
            stmt = stmt.where(Rooms.freeze_reason.isnot(None))
        else:
            stmt = stmt.where(Rooms.freeze_reason.is_(None))

    res = await db.execute(stmt)
    items = res.scalars().all()
    return [Room.model_validate(r) for r in items]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return RoomResponse.model_validate(obj)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, payload: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(**payload.model_dump()))
    await db.commit()
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.patch("/{room_id}/status")
async def change_room_status(room_id: int, status: str, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(room_status=status))
    await db.commit()
    return {"message": "Status updated"}


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    # permanent delete
    await db.delete(obj)
    await db.commit()
    return {"message": "Room deleted"}
