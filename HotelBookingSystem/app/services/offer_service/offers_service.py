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
    offer_data = payload.model_dump()
    room_types = offer_data.pop("room_types", [])  # Extract room_types list of IDs
    if created_by:
        offer_data["created_by"] = created_by

    existing_offer = await fetch_offer_by_name(db, offer_data.get("offer_name"))
    if existing_offer:
        raise HTTPException(status_code=409, detail="Offer with this name already exists")

    room_type_ids = set(room_types)
    provided_ids = {r.get("room_type_id") for r in [] if r.get("room_type_id")}

    # --- Auto-calc pricing if not provided
    if not provided_ids:
        if not room_type_ids:
            raise HTTPException(status_code=400, detail="No room_types provided")

        room_type_objs = await fetch_room_types_by_ids(db, list(room_type_ids))
        found_ids = {rt.room_type_id for rt in room_type_objs}
        missing = room_type_ids - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Invalid room_type_ids: {list(missing)}")

        discount_percent = Decimal(str(offer_data.get("discount_percent", 0)))
        room_pricing_list = [
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

    missing = room_type_ids - {r["room_type_id"] for r in room_pricing_list}
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing pricing for room_type_ids: {list(missing)}")

    created_offer = await insert_offer_record(db, offer_data)
    await insert_offer_room_map(db, created_offer.offer_id, room_pricing_list)
    await db.commit()

    return await fetch_offer_by_id(db, created_offer.offer_id)


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
    offer_record = await fetch_offer_by_id(db, offer_id, include_deleted=True)
    if not offer_record:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer_data = payload.model_dump()
    room_types = offer_data.pop("room_types", [])  # Extract room_types list of IDs
    if updated_by:
        offer_data["created_by"] = updated_by

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
        if attr in offer_data:
            setattr(offer_record, attr, offer_data.get(attr))

    await delete_offer_room_mappings(db, offer_record.offer_id)

    room_type_ids = set(room_types)
    provided_ids = set()  # No pre-provided pricing in update

    if not provided_ids and room_type_ids:
        room_type_objs = await fetch_room_types_by_ids(db, list(room_type_ids))
        discount_percent = Decimal(str(offer_data.get("discount_percent", 0)))
        room_pricing_list = [
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

    await insert_offer_room_map(db, offer_record.offer_id, room_pricing_list)
    await db.commit()
    return await fetch_offer_by_id(db, offer_record.offer_id)


# ==========================================================
# 🔹 SOFT DELETE OFFER
# ==========================================================

async def soft_delete_offer(db: AsyncSession, offer_id: int, deleted_by: Optional[int] = None):
    offer_record = await fetch_offer_by_id(db, offer_id, include_deleted=True)
    if not offer_record:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer_record.is_deleted = True
    await db.commit()
    return {"message": "offer deleted successfully"}
