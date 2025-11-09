from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.reviews import Reviews
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap


# ==========================================================
# CREATE
# ==========================================================
async def insert_review_record(db: AsyncSession, data: dict) -> Reviews:
    review_record = Reviews(**data)
    db.add(review_record)
    await db.flush()
    return review_record


# ==========================================================
# READ
# ==========================================================
async def fetch_review_by_id(db: AsyncSession, review_id: int) -> Optional[Reviews]:
    query_result = await db.execute(select(Reviews).where(Reviews.review_id == review_id))
    return query_result.scalars().first()


async def fetch_booking_by_id(db: AsyncSession, booking_id: int) -> Optional[Bookings]:
    query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    return query_result.scalars().first()


async def fetch_booking_room_map(db: AsyncSession, booking_id: int, room_type_id: Optional[int] = None, room_id: Optional[int] = None):
    stmt = select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    if room_type_id is not None:
        stmt = stmt.where(BookingRoomMap.room_type_id == room_type_id)
    if room_id is not None:
        stmt = stmt.where(BookingRoomMap.room_id == room_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def fetch_reviews_by_user(db: AsyncSession, booking_id: int, user_id: int) -> List[Reviews]:
    query_result = await db.execute(
        select(Reviews).where(Reviews.booking_id == booking_id, Reviews.user_id == user_id)
    )
    return query_result.scalars().all()


async def fetch_reviews_filtered(
    db: AsyncSession,
    booking_id: Optional[int] = None,
    room_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[Reviews]:
    stmt = select(Reviews)
    if booking_id is not None:
        stmt = stmt.where(Reviews.booking_id == booking_id)
    if user_id is not None:
        stmt = stmt.where(Reviews.user_id == user_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


# ==========================================================
# UPDATE
# ==========================================================
async def update_review_record(db: AsyncSession, review: Reviews) -> Reviews:
    db.add(review)
    await db.flush()
    return review
