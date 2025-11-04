from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from decimal import Decimal
from collections import Counter

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap, BookingTaxMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomTypes, RoomStatus
from app.models.sqlalchemy_schemas.tax_utility import TaxUtility
from app.models.pydantic_models.notifications import NotificationCreate
from app.services.notification_service.notifications_service import add_notification as svc_add_notification
from app.models.sqlalchemy_schemas.notifications import Notifications
from app.models.sqlalchemy_schemas.payments import Payments as PaymentsModel
from app.models.pydantic_models.payments import BookingPaymentCreate


async def create_booking(db: AsyncSession, payload) -> Bookings:
    """Create a booking, its room mappings and the booking_tax_map entry.

    - Validates rooms exist and room_type matches
    - Inserts Booking, BookingRoomMap rows
    - Determines applicable tax row from tax_utility and inserts BookingTaxMap
    - Returns hydrated Bookings with rooms and taxes eager-loaded
    """
    data = payload.model_dump()
    # payload.rooms is now a list of room_type ids (ints) requested by client
    # We'll allocate actual room_ids (available rooms) matching these types
    requested_room_type_ids = data.pop("rooms", []) or []

    # Normalize optional foreign keys: treat 0 as None (clients sometimes send 0 for null FK)
    if "offer_id" in data and (data.get("offer_id") == 0):
        data["offer_id"] = None

    # Basic validation
    if not requested_room_type_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No room type ids provided for booking")

    # Verify room_count matches number of requested room types provided
    if data.get("room_count") != len(requested_room_type_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room_count must equal number of requested room types provided")

    # Count how many rooms of each type are requested
    req_counts = Counter(requested_room_type_ids)

    # Fetch available rooms for the requested types
    q = await db.execute(
        select(Rooms).where(Rooms.room_type_id.in_(list(req_counts.keys())), Rooms.room_status == RoomStatus.AVAILABLE)
    )
    available_rooms = q.scalars().all()

    # Group available rooms by room_type_id
    avail_by_type = {}
    for r in available_rooms:
        avail_by_type.setdefault(r.room_type_id, []).append(r)

    # Ensure we have enough available rooms for each requested type
    allocation = []  # will be list of room objects allocated in same order as requested_room_type_ids
    for rt_id in requested_room_type_ids:
        lst = avail_by_type.get(rt_id, [])
        if not lst:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No available rooms for room_type_id {rt_id}")
        # pop one room from the list to allocate
        room_obj = lst.pop(0)
        allocation.append(room_obj)

    # Mark allocated rooms as BOOKED (in same unit-of-work)
    for room_obj in allocation:
        if room_obj.room_status != RoomStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"room_id {room_obj.room_id} is not available for booking")
        room_obj.room_status = RoomStatus.BOOKED

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

    # Create BookingRoomMap records using allocated room objects
    seen = set()
    for room_obj in allocation:
        rid = room_obj.room_id
        if rid in seen:
            continue
        seen.add(rid)
        brm = BookingRoomMap(
            booking_id=booking.booking_id,
            room_id=rid,
            room_type_id=room_obj.room_type_id,
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

    # Create a notification for the booking owner
    try:
        notif_obj = Notifications(
            recipient_user_id=booking.user_id,
            notification_type="TRANSACTIONAL",
            entity_type="BOOKING",
            entity_id=booking.booking_id,
            title="Booking confirmed",
            message=f"Your booking #{booking.booking_id} for {booking.room_count} room(s) has been confirmed. Total: {str(booking.total_price)}",
        )
        db.add(notif_obj)
    except Exception:
        # If building the notification fails, continue without blocking booking creation
        pass
    # If client provided payment details during booking creation, prepare Payments row.
    payment_payload = data.get("payment") if isinstance(data, dict) else None
    if payment_payload:
        # Validate and create payment record now (before final commit) so any DB constraints cause whole transaction to roll back
        bp = None
        try:
            bp = BookingPaymentCreate.model_validate(payment_payload)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment payload: {str(e)}")

        # Basic validation: ensure payment method exists
        from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility

        q = await db.execute(select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == bp.method_id))
        pm = q.scalars().first()
        if not pm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment method_id")

        # Determine payment amount: use booking.total_price by default
        pay_amount = booking.total_price

        pay = PaymentsModel(
            booking_id=booking.booking_id,
            amount=pay_amount,
            method_id=bp.method_id,
            transaction_reference=bp.transaction_reference,
            remarks=bp.remarks,
            user_id=booking.user_id,
        )
        db.add(pay)

    # commit booking (+notification) and payment together
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
