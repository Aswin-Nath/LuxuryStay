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
    """
    Create a new booking and allocate rooms.
    
    Creates a complete booking transaction including:
    1. Validates requested room types and availability
    2. Allocates available rooms based on request
    3. Creates booking record in database
    4. Maps rooms to booking
    5. Maps applicable taxes
    6. Creates payment record
    7. Creates notification for the booking
    
    Room allocation is automatically performed based on room availability and type matching.
    All rooms are marked as BOOKED after successful allocation.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        payload: Pydantic model containing booking details (check_in, check_out, rooms list, total_price, etc).
        user_id (int): The ID of the authenticated user creating the booking.
    
    Returns:
        Bookings: The newly created booking record with booking_id assigned.
    
    Raises:
        HTTPException (400): If no rooms requested, room count mismatch, or no available rooms for requested types.
        HTTPException (400): If any allocated room becomes unavailable during processing.
    """
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

    query = await db.execute(
        select(Rooms).where(Rooms.room_type_id.in_(list(req_counts.keys())), Rooms.room_status == RoomStatus.AVAILABLE)
    )
    available_rooms = query.scalars().all()

    avail_by_type = {}
    for room_record in available_rooms:
        avail_by_type.setdefault(room_record.room_type_id, []).append(room_record)

    allocation = []
    for rt_id in requested_room_type_ids:
        available_rooms_for_type = avail_by_type.get(rt_id, [])
        if not available_rooms_for_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No available rooms for type {rt_id}")
        allocation.append(available_rooms_for_type.pop(0))

    for allocated_room in allocation:
        if allocated_room.room_status != RoomStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"room_id {allocated_room.room_id} unavailable"
            )
        allocated_room.room_status = RoomStatus.BOOKED

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
    for allocated_room in allocation:
        room_id = allocated_room.room_id
        if room_id in seen:
            continue
        seen.add(room_id)
        booking_room_map = BookingRoomMap(
            booking_id=booking.booking_id,
            room_id=room_id,
            room_type_id=allocated_room.room_type_id,
            adults=1,
            children=0,
            offer_discount_percent=0,
        )
        await create_booking_room_map(db, booking_room_map)

    total_price = Decimal(str(data["total_price"]))
    query = await db.execute(select(TaxUtility).where(TaxUtility.is_active == True))
    tax_rows = query.scalars().all()

    chosen_tax = None
    if tax_rows:
        if total_price < Decimal('1000'):
            chosen_tax = next((t for t in tax_rows if t.rate == 0), tax_rows[0])
        elif total_price <= Decimal('7500'):
            chosen_tax = next((t for t in tax_rows if t.rate == 12), tax_rows[0])
        else:
            chosen_tax = next((t for t in tax_rows if t.rate == 18), tax_rows[0])

        tax_amount = (total_price * (Decimal(str(chosen_tax.rate)) / Decimal('100'))).quantize(Decimal('0.01'))
        booking_tax_map = BookingTaxMap(booking_id=booking.booking_id, tax_id=chosen_tax.tax_id, tax_amount=tax_amount)
        await create_booking_tax_map(db, booking_tax_map)

    try:
        notification = Notifications(
            recipient_user_id=booking.user_id,
            notification_type="TRANSACTIONAL",
            entity_type="BOOKING",
            entity_id=booking.booking_id,
            title="Booking confirmed",
            message=f"Your booking #{booking.booking_id} for {booking.room_count} room(s) has been confirmed.",
        )
        db.add(notification)
    except Exception:
        pass

    payment_payload = data.get("payment") if isinstance(data, dict) else None
    if payment_payload:
        try:
            bp = BookingPaymentCreate.model_validate(payment_payload)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment: {str(e)}")

        from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility
        payment_method_query = await db.execute(select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == bp.method_id))
        pm = payment_method_query.scalars().first()
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
    """
    Retrieve a booking by its ID.
    
    Fetches a complete booking record with all associated data.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        booking_id (int): The unique identifier of the booking.
    
    Returns:
        Bookings: The booking record with the specified ID.
    
    Raises:
        HTTPException (404): If booking not found.
    """
    return await get_booking_by_id(db, booking_id)


async def list_bookings(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Bookings]:
    """
    Retrieve a list of all bookings with pagination.
    
    Fetches multiple booking records from the database, limited by the offset and limit parameters.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        limit (int): Maximum number of bookings to return (default: 20).
        offset (int): Number of bookings to skip from the beginning (default: 0).
    
    Returns:
        List[Bookings]: A list of booking records.
    """
    return await list_all_bookings(db, limit=limit, offset=offset)


async def query_bookings(db: AsyncSession, user_id: Optional[int] = None, status: Optional[str] = None):
    """
    Query bookings with optional filters.
    
    Retrieves bookings filtered by user ID and/or booking status. Eagerly loads related rooms and taxes.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        user_id (Optional[int]): Filter by user ID. If None, no user filtering applied.
        status (Optional[str]): Filter by booking status (e.g., 'CONFIRMED', 'CANCELLED', 'COMPLETED'). If None, no status filtering applied.
    
    Returns:
        List[Bookings]: A list of booking records matching the filter criteria, with rooms and taxes loaded.
    """
    stmt = select(Bookings).options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
    if user_id:
        stmt = stmt.where(Bookings.user_id == user_id)
    if status:
        stmt = stmt.where(Bookings.status == status)

    query_result = await db.execute(stmt)
    return query_result.unique().scalars().all()
