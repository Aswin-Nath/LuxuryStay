from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.wishlist import Wishlist


# ==========================================================
# 🔹 CREATE
# ==========================================================

async def create_wishlist_entry(
    db: AsyncSession, user_id: int, room_type_id: Optional[int], offer_id: Optional[int]
) -> Wishlist:
    """
    Create a new wishlist entry for a user.
    
    Inserts a wishlist record linking a user to either a room type or an offer. Exactly
    one of room_type_id or offer_id should be provided (validation done in service layer).
    Flushes and refreshes to populate database-generated fields.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The ID of the user who owns the wishlist item.
        room_type_id (Optional[int]): The ID of the room type to add (None if offer-based).
        offer_id (Optional[int]): The ID of the offer to add (None if room-type-based).
    
    Returns:
        Wishlist: The newly created wishlist record with wishlist_id and timestamps populated.
    """
    wishlist_record = Wishlist(user_id=user_id, room_type_id=room_type_id, offer_id=offer_id)
    db.add(wishlist_record)
    await db.flush()
    await db.refresh(wishlist_record)
    return wishlist_record


# ==========================================================
# 🔹 READ
# ==========================================================

async def get_wishlist_by_user_and_item(
    db: AsyncSession,
    user_id: int,
    room_type_id: Optional[int],
    offer_id: Optional[int],
) -> Optional[Wishlist]:
    """
    Check if a wishlist entry exists for a user and specific item.
    
    Queries for an existing wishlist entry matching the user and either room_type_id or
    offer_id. Used for duplicate prevention (uniqueness check). Only returns non-deleted entries.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The user ID to filter by.
        room_type_id (Optional[int]): The room type ID (if looking for room-type entry).
        offer_id (Optional[int]): The offer ID (if looking for offer entry).
    
    Returns:
        Optional[Wishlist]: The matching wishlist entry if found, None otherwise.
    """
    stmt = select(Wishlist).where(Wishlist.user_id == user_id, Wishlist.is_deleted == False)
    if room_type_id:
        stmt = stmt.where(Wishlist.room_type_id == room_type_id)
    if offer_id:
        stmt = stmt.where(Wishlist.offer_id == offer_id)

    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def get_user_wishlist(
    db: AsyncSession, user_id: int, include_deleted: bool = False
) -> List[Wishlist]:
    """
    Retrieve all wishlist entries for a user.
    
    Fetches all active (or all including soft-deleted) wishlist entries for a specific user.
    Results include both room-type and offer-type items.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The user ID to filter by.
        include_deleted (bool): If True, includes soft-deleted entries (default False).
    
    Returns:
        List[Wishlist]: All active (or all) wishlist items for the user (empty list if none).
    """
    stmt = select(Wishlist).where(Wishlist.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Wishlist.is_deleted == False)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def get_wishlist_by_id(db: AsyncSession, wishlist_id: int) -> Optional[Wishlist]:
    """
    Retrieve a wishlist entry by its ID.
    
    Fetches a single wishlist record by its primary key. Returns both active and
    soft-deleted entries (deletion status check is done in service layer).
    
    Args:
        db (AsyncSession): Database session for executing the query.
        wishlist_id (int): The wishlist entry ID to retrieve.
    
    Returns:
        Optional[Wishlist]: The wishlist record if found, None otherwise.
    """
    stmt = select(Wishlist).where(Wishlist.wishlist_id == wishlist_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


# ==========================================================
# 🔹 UPDATE
# ==========================================================

async def soft_delete_wishlist_entry(db: AsyncSession, wishlist_obj: Wishlist) -> Wishlist:
    """
    Mark a wishlist entry as deleted without removing it from database.
    
    Performs a soft-delete by setting is_deleted to True. The entry remains queryable
    with include_deleted=True flag, supporting audit trails and recovery if needed.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        wishlist_obj (Wishlist): The wishlist object to soft-delete.
    
    Returns:
        Wishlist: The updated wishlist record with is_deleted=True.
    """
    wishlist_obj.is_deleted = True
    db.add(wishlist_obj)
    await db.flush()
    await db.refresh(wishlist_obj)
    return wishlist_obj
