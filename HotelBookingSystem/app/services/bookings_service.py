from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap, BookingTaxMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomTypes, RoomStatus
from app.models.sqlalchemy_schemas.tax_utility import TaxUtility


async def create_booking(db: AsyncSession, payload) -> Bookings:
    """Create a booking, its room mappings and the booking_tax_map entry.

    - Validates rooms exist and room_type matches
    - Inserts Booking, BookingRoomMap rows
    - Determines applicable tax row from tax_utility and inserts BookingTaxMap
    - Returns hydrated Bookings with rooms and taxes eager-loaded
    """
    data = payload.model_dump()
    # payload.rooms is now a list of room ids (ints)
    room_ids = data.pop("rooms", []) or []

    # Basic validation
    if not room_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No room ids provided for booking")

    # Verify room_count matches number of ids provided
    if data.get("room_count") != len(room_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room_count must equal number of room ids provided")

    # Validate each room exists and is available
    q = await db.execute(select(Rooms).where(Rooms.room_id.in_(list(room_ids))))
    room_objs = q.scalars().all()
    found_room_ids = {r.room_id for r in room_objs}
    missing = set(room_ids) - found_room_ids
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid room_ids: {list(missing)}")

    # Map room_id -> room object
    room_map = {r.room_id: r for r in room_objs}

    # Ensure rooms are available and mark them BOOKED (in same unit-of-work)
    for rid in room_ids:
        actual_room = room_map.get(rid)
        if not actual_room:
            continue
        # if room is not AVAILABLE, forbid booking
        if actual_room.room_status != RoomStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"room_id {rid} is not available for booking")
        # mark as booked
        actual_room.room_status = RoomStatus.BOOKED

    # Create Booking
    booking = Bookings(
        user_id=data["user_id"],
        room_count=data["room_count"],
        check_in=data["check_in"],
        check_in_time=data.get("check_in_time"),
        check_out=data["check_out"],
        check_out_time=data.get("check_out_time"),
        total_price=Decimal(str(data["total_price"])),
        offer_id=data.get("offer_id"),
        offer_discount_percent=data.get("offer_discount_percent", 0) or 0,
        primary_customer_name=data.get("primary_customer_name"),
        primary_customer_phone_number=data.get("primary_customer_phone_number"),
        primary_customer_dob=data.get("primary_customer_dob"),
    )
    db.add(booking)
    await db.flush()  # ensure booking.booking_id

    # Create BookingRoomMap records using room info fetched from DB
    seen = set()
    for rid in room_ids:
        if rid in seen:
            continue
        seen.add(rid)
        actual_room = room_map.get(rid)
        brm = BookingRoomMap(
            booking_id=booking.booking_id,
            room_id=rid,
            room_type_id=actual_room.room_type_id,
            adults=1,
            children=0,
            offer_discount_percent=0,
        )
        db.add(brm)

    # Determine tax mapping: pick tax_utility row based on total_price
    # Strategy: find the tax row that most closely matches the booking total
    # (Repository sample has three entries: 0%, 12%, 18%); implement simple thresholds
    total_price = Decimal(str(data["total_price"]))
    q = await db.execute(select(TaxUtility).where(TaxUtility.is_active == True))
    tax_rows = q.scalars().all()

    chosen_tax = None
    # attempt simple heuristic based on rates if present
    if tax_rows:
        # Look for exact 0, 12, 18 pattern if available
        if total_price < Decimal('1000'):
            for t in tax_rows:
                if t.rate == 0:
                    chosen_tax = t
                    break
        elif total_price <= Decimal('7500'):
            for t in tax_rows:
                if t.rate == 12:
                    chosen_tax = t
                    break
        else:
            for t in tax_rows:
                if t.rate == 18:
                    chosen_tax = t
                    break
        # fallback: choose smallest non-zero rate if none matched
        if chosen_tax is None:
            chosen_tax = tax_rows[0]

        tax_amount = (total_price * (Decimal(str(chosen_tax.rate)) / Decimal('100'))).quantize(Decimal('0.01'))
        btm = BookingTaxMap(
            booking_id=booking.booking_id,
            tax_id=chosen_tax.tax_id,
            tax_amount=tax_amount,
        )
        db.add(btm)

    # commit and reload hydrated booking with relations eagerly loaded
    await db.commit()

    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .where(Bookings.booking_id == booking.booking_id)
    )
    res = await db.execute(stmt)
    hydrated = res.scalars().first()
    return hydrated


async def get_booking(db: AsyncSession, booking_id: int) -> Bookings:
    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .where(Bookings.booking_id == booking_id)
    )
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return obj


async def list_bookings(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Bookings]:
    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    items = res.unique().scalars().all()
    return items


async def query_bookings(db: AsyncSession, user_id: Optional[int] = None, status: Optional[str] = None):
    stmt = select(Bookings).options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
    if user_id is not None:
        stmt = stmt.where(Bookings.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Bookings.status == status)

    res = await db.execute(stmt)
    return res.unique().scalars().all()
