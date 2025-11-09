from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal
from collections import Counter
from sqlalchemy.orm import joinedload

# CRUD imports
from app.crud.booking_management.bookings import (
    create_booking_record,
    create_booking_room_map,
    create_booking_tax_map,
    create_payment,
    get_booking_by_id,
    list_all_bookings,
)
# Models
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap, BookingTaxMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus
from app.models.sqlalchemy_schemas.tax_utility import TaxUtility
from app.models.sqlalchemy_schemas.notifications import Notifications
from app.models.sqlalchemy_schemas.payments import Payments as PaymentsModel
from app.schemas.pydantic_models.payments import BookingPaymentCreate


async def create_booking(db: AsyncSession, payload, user_id: int) -> Bookings:
    """Create booking, allocate rooms, map tax, create notification, attach payment."""
    data = payload.model_dump()
    data["user_id"] = user_id  # Enforce user_id from authenticated user
    requested_room_type_ids = data.pop("rooms", []) or []

    if "offer_id" in data and (data.get("offer_id") == 0):
        data["offer_id"] = None

    if not requested_room_type_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No room type ids provided for booking")

    if data.get("room_count") != len(requested_room_type_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="room_count must equal number of requested room types provided",
        )

    req_counts = Counter(requested_room_type_ids)

    q = await db.execute(
        select(Rooms).where(Rooms.room_type_id.in_(list(req_counts.keys())), Rooms.room_status == RoomStatus.AVAILABLE)
    )
    available_rooms = q.scalars().all()

    avail_by_type = {}
    for r in available_rooms:
        avail_by_type.setdefault(r.room_type_id, []).append(r)

    allocation = []
    for rt_id in requested_room_type_ids:
        lst = avail_by_type.get(rt_id, [])
        if not lst:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No available rooms for type {rt_id}")
        allocation.append(lst.pop(0))

    for room_obj in allocation:
        if room_obj.room_status != RoomStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"room_id {room_obj.room_id} unavailable"
            )
        room_obj.room_status = RoomStatus.BOOKED

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

    await create_booking_record(db, booking)

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
        await create_booking_room_map(db, brm)

    total_price = Decimal(str(data["total_price"]))
    q = await db.execute(select(TaxUtility).where(TaxUtility.is_active == True))
    tax_rows = q.scalars().all()

    chosen_tax = None
    if tax_rows:
        if total_price < Decimal('1000'):
            chosen_tax = next((t for t in tax_rows if t.rate == 0), tax_rows[0])
        elif total_price <= Decimal('7500'):
            chosen_tax = next((t for t in tax_rows if t.rate == 12), tax_rows[0])
        else:
            chosen_tax = next((t for t in tax_rows if t.rate == 18), tax_rows[0])

        tax_amount = (total_price * (Decimal(str(chosen_tax.rate)) / Decimal('100'))).quantize(Decimal('0.01'))
        btm = BookingTaxMap(booking_id=booking.booking_id, tax_id=chosen_tax.tax_id, tax_amount=tax_amount)
        await create_booking_tax_map(db, btm)

    try:
        notif_obj = Notifications(
            recipient_user_id=booking.user_id,
            notification_type="TRANSACTIONAL",
            entity_type="BOOKING",
            entity_id=booking.booking_id,
            title="Booking confirmed",
            message=f"Your booking #{booking.booking_id} for {booking.room_count} room(s) has been confirmed.",
        )
        db.add(notif_obj)
    except Exception:
        pass

    payment_payload = data.get("payment") if isinstance(data, dict) else None
    if payment_payload:
        try:
            bp = BookingPaymentCreate.model_validate(payment_payload)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment: {str(e)}")

        from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility
        q = await db.execute(select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == bp.method_id))
        pm = q.scalars().first()
        if not pm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment method_id")

        pay = PaymentsModel(
            booking_id=booking.booking_id,
            amount=booking.total_price,
            method_id=bp.method_id,
            transaction_reference=bp.transaction_reference,
            remarks=bp.remarks,
            user_id=booking.user_id,
        )
        await create_payment(db, pay)

    await db.commit()

    hydrated = await get_booking_by_id(db, booking.booking_id)
    return hydrated


async def get_booking(db: AsyncSession, booking_id: int) -> Bookings:
    return await get_booking_by_id(db, booking_id)


async def list_bookings(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Bookings]:
    return await list_all_bookings(db, limit=limit, offset=offset)


async def query_bookings(db: AsyncSession, user_id: Optional[int] = None, status: Optional[str] = None):
    stmt = select(Bookings).options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
    if user_id:
        stmt = stmt.where(Bookings.user_id == user_id)
    if status:
        stmt = stmt.where(Bookings.status == status)

    res = await db.execute(stmt)
    return res.unique().scalars().all()
