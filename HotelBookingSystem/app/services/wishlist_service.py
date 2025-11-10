from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.wishlist import Wishlist

# CRUD imports
from app.crud.wishlist import (
    create_wishlist_entry,
    get_wishlist_by_user_and_item,
    get_user_wishlist,
    get_wishlist_by_id,
    soft_delete_wishlist_entry,
)


# ==========================================================
# 🔹 ADD TO WISHLIST
# ==========================================================

async def add_to_wishlist(db: AsyncSession, payload, current_user) -> Wishlist:
    """
    Add an item (room type or offer) to user's wishlist.
    
    Creates a wishlist entry for either a room_type_id or offer_id. Enforces uniqueness
    per user and item - duplicate additions are rejected with 409 CONFLICT. Validates that
    at least one of room_type_id or offer_id is provided.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        payload: Pydantic model containing room_type_id and/or offer_id (0 treated as None).
        current_user: The authenticated user (user_id extracted for ownership).
    
    Returns:
        Wishlist: The newly created wishlist entry record.
    
    Raises:
        HTTPException (400): If neither room_type_id nor offer_id is provided.
        HTTPException (409): If item already exists in user's wishlist.
    """
    wishlist_data = payload.model_dump()
    user_id = current_user.user_id
    room_type_id = wishlist_data.get("room_type_id")
    offer_id = wishlist_data.get("offer_id")

    # Normalize optional FKs (0 → None)
    room_type_id = None if room_type_id == 0 else room_type_id
    offer_id = None if offer_id == 0 else offer_id

    if not room_type_id and not offer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either room_type_id or offer_id must be provided",
        )

    # Check uniqueness
    existing_item = await get_wishlist_by_user_and_item(db, user_id, room_type_id, offer_id)
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already in wishlist",
        )

    # Create entry
    wishlist_entry = await create_wishlist_entry(db, user_id, room_type_id, offer_id)
    await db.commit()
    return wishlist_entry


# ==========================================================
# 🔹 LIST USER WISHLIST
# ==========================================================

async def list_user_wishlist(
    db: AsyncSession, user_id: int, include_deleted: bool = False
) -> List[Wishlist]:
    """
    Retrieve all wishlist items for a user.
    
    Fetches the wishlist entries for a specific user, optionally including soft-deleted items.
    Returns all entries regardless of whether they reference room types or offers.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The ID of the user.
        include_deleted (bool): If True, includes soft-deleted wishlist items (default False).
    
    Returns:
        List[Wishlist]: All active (or all) wishlist entries for the user.
    """
    return await get_user_wishlist(db, user_id, include_deleted)


# ==========================================================
# 🔹 REMOVE WISHLIST ITEM
# ==========================================================

async def remove_wishlist(db: AsyncSession, wishlist_id: int, user_id: int):
    """
    Remove a wishlist item by soft-deleting it.
    
    Soft-deletes a wishlist entry for a user. Validates that the user owns the wishlist item
    before deletion. The entry remains in the database marked as deleted for audit purposes.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        wishlist_id (int): The ID of the wishlist item to remove.
        user_id (int): The ID of the current user (must own the item).
    
    Returns:
        dict: Confirmation message {"message": "Wishlist item removed"}.
    
    Raises:
        HTTPException (404): If wishlist item not found.
        HTTPException (403): If user does not own the wishlist item.
    """
    wishlist_entry = await get_wishlist_by_id(db, wishlist_id)
    if not wishlist_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    if wishlist_entry.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to remove this wishlist item",
        )

    await soft_delete_wishlist_entry(db, wishlist_entry)
    await db.commit()
    return {"message": "Wishlist item removed"}
