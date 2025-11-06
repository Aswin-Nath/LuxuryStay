from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.wishlist import Wishlist


async def add_to_wishlist(db: AsyncSession, payload,current_user) -> Wishlist:
    """Create a wishlist entry. Enforce uniqueness per user+item (room_type or offer)."""
    data = payload.model_dump()
    user_id = current_user.user_id
    room_type_id = data.get("room_type_id")
    offer_id = data.get("offer_id")

    # Convert 0 → None for optional FKs
    room_type_id = None if room_type_id == 0 else room_type_id
    offer_id = None if offer_id == 0 else offer_id

    if not room_type_id and not offer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Either room_type_id or offer_id must be provided")

    stmt = select(Wishlist).where(Wishlist.user_id == user_id, Wishlist.is_deleted == False)
    if room_type_id:
        stmt = stmt.where(Wishlist.room_type_id == room_type_id)
    if offer_id:
        stmt = stmt.where(Wishlist.offer_id == offer_id)

    res = await db.execute(stmt)
    existing = res.scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item already in wishlist")

    obj = Wishlist(user_id=user_id, room_type_id=room_type_id, offer_id=offer_id)
    db.add(obj)
    await db.flush()
    await db.commit()

    # Refresh
    await db.refresh(obj)
    return obj


async def list_user_wishlist(db: AsyncSession, user_id: int, include_deleted: bool = False) -> List[Wishlist]:
    stmt = select(Wishlist).where(Wishlist.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Wishlist.is_deleted == False)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def remove_wishlist(db: AsyncSession, wishlist_id: int, user_id: int):
    stmt = select(Wishlist).where(Wishlist.wishlist_id == wishlist_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")
    if obj.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to remove this wishlist item")
    obj.is_deleted = True
    await db.commit()
    return 