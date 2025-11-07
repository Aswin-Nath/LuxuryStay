from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.reviews_management.reviews import (
    insert_review_record,
    fetch_review_by_id,
    fetch_booking_by_id,
    fetch_booking_room_map,
    fetch_reviews_by_user,
    fetch_reviews_filtered,
    update_review_record,
)
from app.models.sqlalchemy_schemas.reviews import Reviews


async def create_review(db: AsyncSession, payload, current_user) -> Reviews:
    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    booking_id = data.get("booking_id")
    room_type_id = data.get("room_type_id") or None

    booking = await fetch_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=400, detail="Invalid booking_id")

    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot review a booking you do not own")

    if room_type_id is not None:
        brm = await fetch_booking_room_map(db, booking_id, room_type_id=room_type_id)
        if not brm:
            raise HTTPException(status_code=400, detail="The provided room_type_id is not part of the booking")

    existing = await fetch_reviews_by_user(db, booking_id, current_user.user_id)
    for ex in existing:
        if ex.room_type_id == room_type_id:
            raise HTTPException(status_code=400, detail="Review already exists for this booking/room")

    rev_data = dict(
        booking_id=booking_id,
        user_id=current_user.user_id,
        room_type_id=room_type_id,
        rating=data.get("rating"),
        comment=data.get("comment"),
    )

    rev = await insert_review_record(db, rev_data)
    await db.commit()
    return await fetch_review_by_id(db, rev.review_id)


async def get_review(db: AsyncSession, review_id: int) -> Reviews:
    rev = await fetch_review_by_id(db, review_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found")
    return rev


async def list_reviews(db: AsyncSession, booking_id=None, room_id=None, user_id=None):
    if room_id is not None and booking_id is None:
        raise HTTPException(status_code=400, detail="booking_id required when filtering by room_id")

    if room_id is not None:
        brm = await fetch_booking_room_map(db, booking_id, room_id=room_id)
        if not brm:
            return []
        return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)

    return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)


async def admin_respond_review(db: AsyncSession, review_id: int, admin_user, admin_response: str) -> Reviews:
    rev = await fetch_review_by_id(db, review_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found")

    rev.admin_id = admin_user.user_id
    rev.admin_response = admin_response
    rev.responded_at = datetime.utcnow()
    await update_review_record(db, rev)
    await db.commit()
    return await fetch_review_by_id(db, review_id)


async def update_review_by_user(db: AsyncSession, review_id: int, payload, current_user) -> Reviews:
    rev = await fetch_review_by_id(db, review_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found")

    if rev.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot modify a review you do not own")

    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    if "rating" in data and data["rating"] is not None:
        rev.rating = data["rating"]
    if "comment" in data and data["comment"] is not None:
        rev.comment = data["comment"]

    await update_review_record(db, rev)
    await db.commit()
    return await fetch_review_by_id(db, review_id)
