from typing import List, Optional
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD imports
from app.crud.offers_management.offers import (
    insert_offer_record,
    fetch_offer_by_name,
    fetch_offer_by_id,
    fetch_offers_list,
    delete_offer_room_mappings,
    insert_offer_room_map,
    fetch_room_types_by_ids,
)
from app.models.sqlalchemy_schemas.offers import Offer


# ==========================================================
# 🔹 CREATE OFFER
# ==========================================================

async def create_offer(db: AsyncSession, payload, created_by: Optional[int] = None) -> Offer:
    data = payload.model_dump()
    rooms = data.pop("rooms", [])
    if created_by:
        data["created_by"] = created_by

    existing = await fetch_offer_by_name(db, data.get("offer_name"))
    if existing:
        raise HTTPException(status_code=409, detail="Offer with this name already exists")

    room_type_ids = set(data.get("room_types", []))
    provided_ids = {r.get("room_type_id") for r in rooms if r.get("room_type_id")}

    # --- Auto-calc pricing if not provided
    if not provided_ids:
        if not room_type_ids:
            raise HTTPException(status_code=400, detail="No room_types provided")

        room_type_objs = await fetch_room_types_by_ids(db, list(room_type_ids))
        found_ids = {rt.room_type_id for rt in room_type_objs}
        missing = room_type_ids - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Invalid room_type_ids: {list(missing)}")

        discount_percent = Decimal(str(data.get("discount_percent", 0)))
        rooms = [
            {
                "room_type_id": rt.room_type_id,
                "actual_price": Decimal(str(rt.price_per_night)),
                "discounted_price": (
                    Decimal(str(rt.price_per_night))
                    * (Decimal("1") - discount_percent / Decimal("100"))
                ).quantize(Decimal("0.01")),
            }
            for rt in room_type_objs
        ]

    missing = room_type_ids - {r["room_type_id"] for r in rooms}
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing pricing for room_type_ids: {list(missing)}")

    offer = await insert_offer_record(db, data)
    await insert_offer_room_map(db, offer.offer_id, rooms)
    await db.commit()

    return await fetch_offer_by_id(db, offer.offer_id)


# ==========================================================
# 🔹 GET OFFER
# ==========================================================

async def get_offer(db: AsyncSession, offer_id: int, include_deleted: bool = False) -> Offer:
    offer = await fetch_offer_by_id(db, offer_id, include_deleted)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


# ==========================================================
# 🔹 LIST OFFERS
# ==========================================================

async def list_offers(db: AsyncSession, limit: int = 20, offset: int = 0, include_deleted: bool = False) -> List[Offer]:
    return await fetch_offers_list(db, limit, offset, include_deleted)


# ==========================================================
# 🔹 UPDATE OFFER
# ==========================================================

async def update_offer(db: AsyncSession, offer_id: int, payload, updated_by: Optional[int] = None) -> Offer:
    offer = await fetch_offer_by_id(db, offer_id, include_deleted=True)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    data = payload.model_dump()
    rooms = data.pop("rooms", [])
    if updated_by:
        data["created_by"] = updated_by

    for attr in (
        "offer_name",
        "description",
        "offer_items",
        "discount_percent",
        "start_date",
        "expiry_date",
        "offer_price",
        "visibility_status",
    ):
        if attr in data:
            setattr(offer, attr, data.get(attr))

    await delete_offer_room_mappings(db, offer.offer_id)

    room_type_ids = set(data.get("room_types", []))
    provided_ids = {r.get("room_type_id") for r in rooms if r.get("room_type_id")}

    if not provided_ids and room_type_ids:
        room_type_objs = await fetch_room_types_by_ids(db, list(room_type_ids))
        discount_percent = Decimal(str(data.get("discount_percent", 0)))
        rooms = [
            {
                "room_type_id": rt.room_type_id,
                "actual_price": Decimal(str(rt.price_per_night)),
                "discounted_price": (
                    Decimal(str(rt.price_per_night))
                    * (Decimal("1") - discount_percent / Decimal("100"))
                ).quantize(Decimal("0.01")),
            }
            for rt in room_type_objs
        ]

    await insert_offer_room_map(db, offer.offer_id, rooms)
    await db.commit()
    return await fetch_offer_by_id(db, offer.offer_id)


# ==========================================================
# 🔹 SOFT DELETE OFFER
# ==========================================================

async def soft_delete_offer(db: AsyncSession, offer_id: int, deleted_by: Optional[int] = None):
    offer = await fetch_offer_by_id(db, offer_id, include_deleted=True)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer.is_deleted = True
    await db.commit()
    return {"message": "offer deleted successfully"}
