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
    """Insert a new wishlist record."""
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
    """Fetch wishlist entry for a given user and room_type/offer."""
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
    """Fetch all wishlist entries for a given user."""
    stmt = select(Wishlist).where(Wishlist.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Wishlist.is_deleted == False)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def get_wishlist_by_id(db: AsyncSession, wishlist_id: int) -> Optional[Wishlist]:
    """Fetch a wishlist entry by its ID."""
    stmt = select(Wishlist).where(Wishlist.wishlist_id == wishlist_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


# ==========================================================
# 🔹 UPDATE
# ==========================================================

async def soft_delete_wishlist_entry(db: AsyncSession, wishlist_obj: Wishlist) -> Wishlist:
    """Soft-delete a wishlist entry."""
    wishlist_obj.is_deleted = True
    db.add(wishlist_obj)
    await db.flush()
    await db.refresh(wishlist_obj)
    return wishlist_obj
