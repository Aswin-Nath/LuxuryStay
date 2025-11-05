from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import datetime

from app.models.sqlalchemy_schemas.reviews import Reviews
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap


async def create_review(db: AsyncSession, payload, current_user) -> Reviews:
    # Accept either a Pydantic model (with model_dump) or a plain dict
    if hasattr(payload, "model_dump"):
        data = payload.model_dump()
    elif isinstance(payload, dict):
        data = payload
    else:
        # try to coerce
        try:
            data = dict(payload)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    booking_id = data.get("booking_id")
    room_type_id = data.get("room_type_id")
    if room_type_id==0:
        room_type_id=None
    # Validate booking exists
    res = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    booking = res.scalars().first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid booking_id")

    # Only the booking owner can create a review for that booking
    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot review a booking you do not own")

    # If room_type_id provided, ensure the booking contains that room type
    if room_type_id is not None:
        q = await db.execute(
            select(BookingRoomMap).where(
                BookingRoomMap.booking_id == booking_id,
                BookingRoomMap.room_type_id == room_type_id,
            )
        )
        brm = q.scalars().first()
        if not brm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The provided room_type_id is not part of the booking")

    # Prevent duplicate reviews by same user for same booking+room_type combination
    q = await db.execute(select(Reviews).where(Reviews.booking_id == booking_id, Reviews.user_id == current_user.user_id))
    existing = q.scalars().all()
    for ex in existing:
        # both None or equal
        if ex.room_type_id == room_type_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted a review for this booking/room")

    # Create review
    rev = Reviews(
        booking_id=booking_id,
        user_id=current_user.user_id,
        room_type_id=room_type_id,
        rating=data.get("rating"),
        comment=data.get("comment"),
    )
    db.add(rev)
    await db.flush()
    await db.commit()

    # Reload and return
    stmt = select(Reviews).where(Reviews.review_id == rev.review_id)
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_review(db: AsyncSession, review_id: int) -> Reviews:
    stmt = select(Reviews).where(Reviews.review_id == review_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return obj


async def list_reviews(db: AsyncSession, booking_id: Optional[int] = None, room_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Reviews]:
    """List reviews with optional filters.

    - booking_id: filter reviews for a booking
    - room_id: if provided, resolves to the room_type_id for the given booking and filters by that room_type
    - user_id: filter reviews by reviewer
    """
    stmt = select(Reviews)
    # If room_id is provided we require booking_id to resolve the room_type for the booking
    if room_id is not None:
        if booking_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="booking_id is required when filtering by room_id")
        # resolve room_id -> room_type_id for this booking
        q = await db.execute(
            select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id, BookingRoomMap.room_id == room_id)
        )
        brm = q.scalars().first()
        if not brm:
            # no mapping found; return empty list
            return []
        stmt = stmt.where(Reviews.room_type_id == brm.room_type_id)

    if booking_id is not None:
        stmt = stmt.where(Reviews.booking_id == booking_id)

    if user_id is not None:
        stmt = stmt.where(Reviews.user_id == user_id)

    res = await db.execute(stmt)
    return res.scalars().all()


async def admin_respond_review(db: AsyncSession, review_id: int, admin_user, admin_response: str) -> Reviews:
    stmt = select(Reviews).where(Reviews.review_id == review_id)
    res = await db.execute(stmt)
    rev = res.scalars().first()
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    rev.admin_id = admin_user.user_id
    rev.admin_response = admin_response
    rev.responded_at = datetime.utcnow()
    db.add(rev)
    await db.commit()

    stmt = select(Reviews).where(Reviews.review_id == review_id)
    res = await db.execute(stmt)
    return res.scalars().first()


async def update_review_by_user(db: AsyncSession, review_id: int, payload, current_user) -> Reviews:
    """Allow the review owner to update rating and comment."""
    stmt = select(Reviews).where(Reviews.review_id == review_id)
    res = await db.execute(stmt)
    rev = res.scalars().first()
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    # Only the original reviewer may update their review
    if rev.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify a review you do not own")

    data = payload.model_dump() if hasattr(payload, 'model_dump') else dict(payload)
    # Apply allowed updates
    if 'rating' in data and data['rating'] is not None:
        rev.rating = data['rating']
    if 'comment' in data and data['comment'] is not None:
        rev.comment = data['comment']
    db.add(rev)
    await db.commit()

    stmt = select(Reviews).where(Reviews.review_id == review_id)
    res = await db.execute(stmt)
    return res.scalars().first()
