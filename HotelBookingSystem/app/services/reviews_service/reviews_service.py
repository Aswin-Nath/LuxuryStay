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
    review_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    booking_id = review_data.get("booking_id")
    room_type_id = review_data.get("room_type_id") or None

    booking_record = await fetch_booking_by_id(db, booking_id)
    if not booking_record:
        raise HTTPException(status_code=400, detail="Invalid booking_id")

    if booking_record.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot review a booking you do not own")

    if room_type_id is not None:
        booking_room_mapping = await fetch_booking_room_map(db, booking_id, room_type_id=room_type_id)
        if not booking_room_mapping:
            raise HTTPException(status_code=400, detail="The provided room_type_id is not part of the booking")

    existing_reviews = await fetch_reviews_by_user(db, booking_id, current_user.user_id)
    for existing_review in existing_reviews:
        if existing_review.room_type_id == room_type_id:
            raise HTTPException(status_code=400, detail="Review already exists for this booking/room")

    review_payload = dict(
        booking_id=booking_id,
        user_id=current_user.user_id,
        room_type_id=room_type_id,
        rating=review_data.get("rating"),
        comment=review_data.get("comment"),
    )

    review_record = await insert_review_record(db, review_payload)
    await db.commit()
    return await fetch_review_by_id(db, review_record.review_id)


async def get_review(db: AsyncSession, review_id: int) -> Reviews:
    review_record = await fetch_review_by_id(db, review_id)
    if not review_record:
        raise HTTPException(status_code=404, detail="Review not found")
    return review_record


async def list_reviews(db: AsyncSession, booking_id=None, room_id=None, user_id=None):
    if room_id is not None and booking_id is None:
        raise HTTPException(status_code=400, detail="booking_id required when filtering by room_id")

    if room_id is not None:
        booking_room_mapping = await fetch_booking_room_map(db, booking_id, room_id=room_id)
        if not booking_room_mapping:
            return []
        return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)

    return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)


async def admin_respond_review(db: AsyncSession, review_id: int, admin_user, admin_response: str) -> Reviews:
    review_record = await fetch_review_by_id(db, review_id)
    if not review_record:
        raise HTTPException(status_code=404, detail="Review not found")

    review_record.admin_id = admin_user.user_id
    review_record.admin_response = admin_response
    review_record.responded_at = datetime.utcnow()
    await update_review_record(db, review_record)
    await db.commit()
    return await fetch_review_by_id(db, review_id)


async def update_review_by_user(db: AsyncSession, review_id: int, payload, current_user) -> Reviews:
    review_record = await fetch_review_by_id(db, review_id)
    if not review_record:
        raise HTTPException(status_code=404, detail="Review not found")

    if review_record.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot modify a review you do not own")

    update_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    if "rating" in update_data and update_data["rating"] is not None:
        review_record.rating = update_data["rating"]
    if "comment" in update_data and update_data["comment"] is not None:
        review_record.comment = update_data["comment"]

    await update_review_record(db, review_record)
    await db.commit()
    return await fetch_review_by_id(db, review_id)
