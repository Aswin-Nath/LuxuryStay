from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.rooms import Rooms


async def create_room(db: AsyncSession, payload) -> Rooms:
    """Create a room ensuring room_no is unique."""
    q = await db.execute(select(Rooms).where(Rooms.room_no == payload.room_no))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    obj = Rooms(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_rooms(
    db: AsyncSession,
    room_type_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    is_freezed: Optional[bool] = None,
) -> List[Rooms]:
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
    return items


async def get_room(db: AsyncSession, room_id: int) -> Rooms:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return obj


async def update_room(db: AsyncSession, room_id: int, payload) -> Rooms:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(**payload.model_dump()))
    await db.commit()
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    return obj


async def change_room_status(db: AsyncSession, room_id: int, status_value: str) -> None:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(room_status=status_value))
    await db.commit()


async def delete_room(db: AsyncSession, room_id: int) -> None:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.delete(obj)
    await db.commit()
