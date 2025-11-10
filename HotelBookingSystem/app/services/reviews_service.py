from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.reviews import (
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
    """
    Create a new review for a booking.
    
    Validates that the user owns the booking and hasn't already reviewed the same room.
    A user can review a whole booking or specific room types within the booking.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        payload: Pydantic model containing review data (booking_id, room_type_id, rating, comment).
        current_user: The authenticated user creating the review.
    
    Returns:
        Reviews: The newly created review record.
    
    Raises:
        HTTPException (400): If booking_id is invalid or room_type_id is not part of the booking.
        HTTPException (403): If user doesn't own the booking.
        HTTPException (400): If review already exists for this booking/room combination.
    """
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
    """
    Retrieve a single review by ID.
    
    Fetches a review record from the database.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        review_id (int): The unique identifier of the review.
    
    Returns:
        Reviews: The review record.
    
    Raises:
        HTTPException (404): If review not found.
    """
    review_record = await fetch_review_by_id(db, review_id)
    if not review_record:
        raise HTTPException(status_code=404, detail="Review not found")
    return review_record


async def list_reviews(db: AsyncSession, booking_id=None, room_id=None, user_id=None):
    """
    List reviews with optional filters.
    
    Retrieves reviews filtered by booking, room, and/or user. If filtering by room, booking_id must be provided.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        booking_id (int, optional): Filter by booking ID.
        room_id (int, optional): Filter by room ID (requires booking_id).
        user_id (int, optional): Filter by user ID.
    
    Returns:
        List[Reviews]: List of review records matching filter criteria.
    
    Raises:
        HTTPException (400): If room_id is provided without booking_id.
    """
    if room_id is not None and booking_id is None:
        raise HTTPException(status_code=400, detail="booking_id required when filtering by room_id")

    if room_id is not None:
        booking_room_mapping = await fetch_booking_room_map(db, booking_id, room_id=room_id)
        if not booking_room_mapping:
            return []
        return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)

    return await fetch_reviews_filtered(db, booking_id=booking_id, user_id=user_id)


async def admin_respond_review(db: AsyncSession, review_id: int, admin_user, admin_response: str) -> Reviews:
    """
    Add an admin response to a customer review.
    
    Allows an admin or manager to respond to a review with their own comment.
    Updates the response timestamp and admin user ID.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        review_id (int): The ID of the review to respond to.
        admin_user: The authenticated admin user.
        admin_response (str): The admin's response message.
    
    Returns:
        Reviews: The updated review record with admin response.
    
    Raises:
        HTTPException (404): If review not found.
    """
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
