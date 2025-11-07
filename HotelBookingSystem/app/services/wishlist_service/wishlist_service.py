from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.wishlist import Wishlist

# CRUD imports
from app.crud.wishlist_management.wishlist import (
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
    """Create a wishlist entry. Enforce uniqueness per user+item (room_type or offer)."""
    data = payload.model_dump()
    user_id = current_user.user_id
    room_type_id = data.get("room_type_id")
    offer_id = data.get("offer_id")

    # Normalize optional FKs (0 → None)
    room_type_id = None if room_type_id == 0 else room_type_id
    offer_id = None if offer_id == 0 else offer_id

    if not room_type_id and not offer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either room_type_id or offer_id must be provided",
        )

    # Check uniqueness
    existing = await get_wishlist_by_user_and_item(db, user_id, room_type_id, offer_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already in wishlist",
        )

    # Create entry
    obj = await create_wishlist_entry(db, user_id, room_type_id, offer_id)
    await db.commit()
    return obj


# ==========================================================
# 🔹 LIST USER WISHLIST
# ==========================================================

async def list_user_wishlist(
    db: AsyncSession, user_id: int, include_deleted: bool = False
) -> List[Wishlist]:
    """Return all wishlist items for the user."""
    return await get_user_wishlist(db, user_id, include_deleted)


# ==========================================================
# 🔹 REMOVE WISHLIST ITEM
# ==========================================================

async def remove_wishlist(db: AsyncSession, wishlist_id: int, user_id: int):
    """Soft-delete a wishlist item for a user."""
    obj = await get_wishlist_by_id(db, wishlist_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    if obj.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to remove this wishlist item",
        )

    await soft_delete_wishlist_entry(db, obj)
    await db.commit()
    return {"message": "Wishlist item removed"}
