from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms


# ==========================================================
# 🔹 CREATE
# ==========================================================

async def insert_refund_record(db: AsyncSession, data: dict) -> Refunds:
    refund_record = Refunds(**data)
    db.add(refund_record)
    await db.flush()
    return refund_record


async def insert_refund_room_map(db: AsyncSession, data: dict) -> RefundRoomMap:
    refund_room_map_record = RefundRoomMap(**data)
    db.add(refund_room_map_record)
    await db.flush()
    return refund_room_map_record


# ==========================================================
# 🔹 READ
# ==========================================================

async def fetch_refund_by_id(db: AsyncSession, refund_id: int) -> Optional[Refunds]:
    query_result = await db.execute(select(Refunds).where(Refunds.refund_id == refund_id))
    return query_result.scalars().first()


async def fetch_booking_by_id(db: AsyncSession, booking_id: int) -> Optional[Bookings]:
    query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    return query_result.scalars().first()


async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
    query_result = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    return query_result.scalars().first()


async def fetch_booking_room_maps(db: AsyncSession, booking_id: int) -> List[BookingRoomMap]:
    query_result = await db.execute(select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id))
    return query_result.scalars().all()


async def fetch_refunds_filtered(
    db: AsyncSession,
    refund_id: Optional[int] = None,
    booking_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[Refunds]:
    stmt = select(Refunds)
    if refund_id is not None:
        stmt = stmt.where(Refunds.refund_id == refund_id)
    if booking_id is not None:
        stmt = stmt.where(Refunds.booking_id == booking_id)
    if user_id is not None:
        stmt = stmt.where(Refunds.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Refunds.status == status)
    if type is not None:
        stmt = stmt.where(Refunds.type == type)
    if from_date is not None:
        stmt = stmt.where(Refunds.initiated_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Refunds.initiated_at <= to_date)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()
