from typing import List, Optional
from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from decimal import Decimal

from app.models.sqlalchemy_schemas.offers import Offer, OfferRoomMap
from app.models.sqlalchemy_schemas.rooms import RoomTypes
from app.models.sqlalchemy_schemas.users import Users


async def create_offer(db: AsyncSession, payload, created_by: int | None = None) -> Offer:
    """Create an Offer and its OfferRoomMap entries, preloading all relations for async-safe Pydantic serialization."""
    data = payload.model_dump()
    rooms = data.pop("rooms", [])
    
    if created_by is not None:
        data["created_by"] = created_by

    # --- Uniqueness check
    existing = await db.scalar(select(Offer.offer_id).where(Offer.offer_name == data.get("offer_name")))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer with this name already exists")

    # --- Validate and build room mappings
    room_type_ids = {rt for rt in data.get("room_types", [])}
    provided_ids = {r.get("room_type_id") for r in rooms if r.get("room_type_id") is not None}

    if not provided_ids:
        if not room_type_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No room_types provided")

        q = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id.in_(list(room_type_ids))))
        room_type_objs = q.scalars().all()
        found_ids = {rt.room_type_id for rt in room_type_objs}
        missing = room_type_ids - found_ids
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid room_type_ids: {list(missing)}")

        discount_percent = Decimal(str(data.get("discount_percent", 0)))
        rooms = []
        for rt in room_type_objs:
            actual = Decimal(str(rt.price_per_night))
            discounted = (actual * (Decimal('1') - (discount_percent / Decimal('100')))).quantize(Decimal('0.01'))
            rooms.append({
                "room_type_id": rt.room_type_id,
                "actual_price": actual,
                "discounted_price": discounted
            })
        provided_ids = {r["room_type_id"] for r in rooms}

    missing = room_type_ids - provided_ids
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing pricing for room_type_ids: {list(missing)}")

    # --- Create Offer record
    offer = Offer(
        offer_name=data["offer_name"],
        description=data.get("description"),
        offer_items=data.get("offer_items"),
        discount_percent=data["discount_percent"],
        start_date=data["start_date"],
        expiry_date=data["expiry_date"],
        created_by=data.get("created_by"),
        offer_price=data.get("offer_price"),
    )
    db.add(offer)
    await db.flush()  # Ensure offer_id is generated

    # --- Create OfferRoomMap records
    seen = set()
    for r in rooms:
        rt_id = r["room_type_id"]
        if rt_id in seen:
            continue
        seen.add(rt_id)
        orm = OfferRoomMap(
            offer_id=offer.offer_id,
            room_type_id=rt_id,
            actual_price=Decimal(str(r["actual_price"])),
            discounted_price=Decimal(str(r["discounted_price"])),
        )
        db.add(orm)

    # --- Commit and fetch hydrated Offer with all joins
    await db.commit()

    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .where(Offer.offer_id == offer.offer_id)
    )
    res = await db.execute(stmt)
    hydrated_offer = res.scalars().first()

    return hydrated_offer

async def get_offer(db: AsyncSession, offer_id: int, include_deleted: bool = False) -> Offer:
    """
    Fetch a single offer with all room mappings and room type info.
    No aliasing, no property indirection.
    """
    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .where(Offer.offer_id == offer_id)
    )
    if not include_deleted:
        stmt = stmt.where(Offer.is_deleted == False)

    res = await db.execute(stmt)
    obj = res.scalars().first()

    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    return obj


async def list_offers(db: AsyncSession, limit: int = 20, offset: int = 0, include_deleted: bool = False) -> List[Offer]:
    """
    Fetch multiple offers with their room mappings and related room types.
    """
    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .limit(limit)
        .offset(offset)
    )
    if not include_deleted:
        stmt = stmt.where(Offer.is_deleted == False)

    res = await db.execute(stmt)
    items = res.unique().scalars().all()
    return items


async def update_offer(db: AsyncSession, offer_id: int, payload, updated_by: int | None = None) -> Offer:
    """Update an existing offer and its room mappings (async-safe eager loaded return)."""
    
    # --- Fetch existing offer
    q = await db.execute(select(Offer).where(Offer.offer_id == offer_id))
    offer = q.scalars().first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    data = payload.model_dump()
    rooms = data.pop("rooms", [])
    if updated_by is not None:
        data["created_by"] = updated_by
    
    # --- Update scalar fields (include offer_price)
    for attr in (
        "offer_name",
        "description",
        "offer_items",
        "discount_percent",
        "start_date",
        "expiry_date",
        "offer_price",
        "visibility_status"
    ):
        if attr in data:
            setattr(offer, attr, data.get(attr))

    # --- Delete existing mappings
    await db.execute(delete(OfferRoomMap).where(OfferRoomMap.offer_id == offer.offer_id))

    # --- Build mappings again
    room_type_ids = {rt for rt in data.get("room_types", [])}
    provided_ids = {r.get("room_type_id") for r in rooms if r.get("room_type_id") is not None}

    if not provided_ids:
        if not room_type_ids:
            await db.commit()
            # ✅ Reload fully to prevent MissingGreenlet
            stmt = (
                select(Offer)
                .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
                .where(Offer.offer_id == offer.offer_id)
            )
            res = await db.execute(stmt)
            return res.scalars().first()

        q = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id.in_(list(room_type_ids))))
        room_type_objs = q.scalars().all()
        found_ids = {rt.room_type_id for rt in room_type_objs}
        missing = room_type_ids - found_ids
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid room_type_ids: {list(missing)}")

        discount_percent = Decimal(str(data.get("discount_percent", 0)))
        rooms = []
        for rt in room_type_objs:
            actual = Decimal(str(rt.price_per_night))
            discounted = (actual * (Decimal('1') - (discount_percent / Decimal('100')))).quantize(Decimal('0.01'))
            rooms.append({
                "room_type_id": rt.room_type_id,
                "actual_price": actual,
                "discounted_price": discounted,
            })

    # --- Add new mappings
    seen = set()
    for r in rooms:
        rt_id = r["room_type_id"]
        if rt_id in seen:
            continue
        seen.add(rt_id)
        orm = OfferRoomMap(
            offer_id=offer.offer_id,
            room_type_id=rt_id,
            actual_price=Decimal(str(r["actual_price"])),
            discounted_price=Decimal(str(r["discounted_price"])),
        )
        db.add(orm)

    # --- Commit changes and reload hydrated offer
    await db.commit()

    stmt = (
        select(Offer)
        .options(joinedload(Offer.room_mappings).joinedload(OfferRoomMap.room_type))
        .where(Offer.offer_id == offer.offer_id)
    )
    res = await db.execute(stmt)
    hydrated_offer = res.scalars().first()

    return hydrated_offer


async def soft_delete_offer(db: AsyncSession, offer_id: int, deleted_by: int | None = None):
    q = await db.execute(select(Offer).where(Offer.offer_id == offer_id))
    offer = q.scalars().first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    offer.is_deleted = True
    await db.commit()
    return {"message":"offer deleted successfully"}