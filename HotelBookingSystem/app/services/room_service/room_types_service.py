from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.rooms import RoomTypes


async def create_room_type(db: AsyncSession, payload) -> RoomTypes:
    q = await db.execute(select(RoomTypes).where(RoomTypes.type_name == payload.type_name))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type already exists")

    obj = RoomTypes(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_room_types(db: AsyncSession, include_deleted: Optional[bool] = False) -> List[RoomTypes]:
    stmt = select(RoomTypes)
    if not include_deleted:
        stmt = stmt.where(RoomTypes.is_deleted == False)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def get_room_type(db: AsyncSession, room_type_id: int) -> RoomTypes:
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return obj


async def update_room_type(db: AsyncSession, room_type_id: int, payload) -> RoomTypes:
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    # Only update fields provided by the client to avoid overwriting existing values.
    data = payload.model_dump(exclude_unset=True)
    if data:
        await db.execute(
            update(RoomTypes)
            .where(RoomTypes.room_type_id == room_type_id)
            .values(**data)
        )
    await db.commit()
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    return obj


async def soft_delete_room_type(db: AsyncSession, room_type_id: int) -> None:
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    await db.execute(update(RoomTypes).where(RoomTypes.room_type_id == room_type_id).values(is_deleted=True))
    await db.commit()
