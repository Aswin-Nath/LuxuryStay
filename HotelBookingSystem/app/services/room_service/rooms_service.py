from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.rooms import Rooms, RoomTypes


async def create_room(db: AsyncSession, payload) -> Rooms:
    q = await db.execute(select(Rooms).where(Rooms.room_no == payload.room_no))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    # Fetch room type to derive price and occupancy limits
    rt_res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == payload.room_type_id))
    room_type = rt_res.scalars().first()
    if not room_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    # For creation, use full payload (required fields must be present).
    data = payload.model_dump()
    # populate derived fields from room type
    data["price_per_night"] = room_type.price_per_night
    data["max_adult_count"] = room_type.max_adult_count
    data["max_child_count"] = room_type.max_child_count

    obj = Rooms(**data)
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

    # Apply only fields explicitly provided by client to avoid overwriting existing values.
    data = payload.model_dump(exclude_unset=True)
    # If room_type_id changed (or provided), fetch derived values and set them

    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(**data))
    await db.commit()
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    return obj





async def delete_room(db: AsyncSession, room_id: int) -> None:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.delete(obj)
    await db.commit()
