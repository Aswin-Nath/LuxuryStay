from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.sqlalchemy_schemas.offers import Offer, OfferRoomMap
from app.models.sqlalchemy_schemas.rooms import RoomTypes


# ==========================================================
# 🔹 OFFER CORE CRUD
# ==========================================================

async def insert_offer_record(db: AsyncSession, data: dict) -> Offer:
    offer = Offer(**data)
    db.add(offer)
    await db.flush()
    return offer


async def fetch_offer_by_name(db: AsyncSession, offer_name: str):
    return await db.scalar(select(Offer.offer_id).where(Offer.offer_name == offer_name))


async def fetch_offer_by_id(db: AsyncSession, offer_id: int, include_deleted: bool = False) -> Optional[Offer]:
    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .where(Offer.offer_id == offer_id)
    )
    if not include_deleted:
        stmt = stmt.where(Offer.is_deleted == False)
    res = await db.execute(stmt)
    return res.scalars().first()


async def fetch_offers_list(db: AsyncSession, limit: int = 20, offset: int = 0, include_deleted: bool = False) -> List[Offer]:
    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .limit(limit)
        .offset(offset)
    )
    if not include_deleted:
        stmt = stmt.where(Offer.is_deleted == False)
    res = await db.execute(stmt)
    return res.unique().scalars().all()


async def delete_offer_room_mappings(db: AsyncSession, offer_id: int):
    await db.execute(delete(OfferRoomMap).where(OfferRoomMap.offer_id == offer_id))


async def insert_offer_room_map(db: AsyncSession, offer_id: int, rooms: List[dict]):
    seen = set()
    for r in rooms:
        rt_id = r["room_type_id"]
        if rt_id in seen:
            continue
        seen.add(rt_id)
        orm = OfferRoomMap(
            offer_id=offer_id,
            room_type_id=rt_id,
            actual_price=Decimal(str(r["actual_price"])),
            discounted_price=Decimal(str(r["discounted_price"])),
        )
        db.add(orm)


async def fetch_room_types_by_ids(db: AsyncSession, room_type_ids: List[int]) -> List[RoomTypes]:
    q = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id.in_(room_type_ids)))
    return q.scalars().all()
