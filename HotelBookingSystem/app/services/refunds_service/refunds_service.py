from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime

from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus
from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility


async def cancel_booking_and_create_refund(db: AsyncSession, booking_id: int, payload, current_user):
    """Cancel a booking and create a refund record (transaction details may be filled later).

    payload should provide: full_cancellation (bool), refund_amount (optional), refund_rooms (optional list of room_ids), transaction_method_id (optional), transaction_number (optional), remarks (optional)
    """
    # Fetch booking
    res = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    booking = res.scalars().first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Only owner or privileged user should cancel; enforce owner for now
    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel a booking you do not own")

    data = payload.model_dump() if hasattr(payload, 'model_dump') else dict(payload)

    # If refund_rooms not provided, treat as full cancellation
    refund_rooms = data.get('refund_rooms') or []
    full_cancel = bool(data.get('full_cancellation', False)) or (len(refund_rooms) == 0)

    # determine number of nights for per-room price calculations
    nights = (booking.check_out - booking.check_in).days
    if nights <= 0:
        nights = 1
    # Fetch booking room mappings to compute per-room prices
    qbr = await db.execute(select(BookingRoomMap).where(BookingRoomMap.booking_id == booking.booking_id))
    brm_items = qbr.scalars().all()
    # Map room_id -> BookingRoomMap
    brm_by_room = {b.room_id: b for b in brm_items}

    # Helper to compute room total price (price_per_night * nights)
    async def room_total_price(room_id: int) -> Decimal:
        q = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
        room = q.scalars().first()
        if not room:
            return Decimal('0')
        return (Decimal(str(room.price_per_night)) * Decimal(nights)).quantize(Decimal('0.01'))

    # Determine refund amount and per-room breakdown
    per_room_refunds: dict[int, Decimal] = {}
    if full_cancel:
        # full: refund is booking total, and every room gets its full room price
        refund_amount = Decimal(str(booking.total_price))
        for b in brm_items:
            amt = await room_total_price(b.room_id)
            per_room_refunds[b.room_id] = amt
    else:
        # partial: refund_rooms must be provided and each room's refund is its room price
        if not refund_rooms:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refund_rooms must be provided for partial cancellations")
        total = Decimal('0')
        for rid in refund_rooms:
            amt = await room_total_price(rid)
            per_room_refunds[rid] = amt
            total += amt
        refund_amount = total.quantize(Decimal('0.01'))

    # Create Refunds entry (transaction fields nullable)
    rf = Refunds(
        booking_id=booking.booking_id,
        user_id=current_user.user_id,
        type='CANCELLATION' if full_cancel else "PARTIAL_CANCEL",
        status='INITIATED',
        refund_amount=refund_amount,
        remarks=data.get('remarks'),
        transaction_method_id=data.get('transaction_method_id'),
        transaction_number=data.get('transaction_number'),
    )
    db.add(rf)
    await db.flush()

    # Create RefundRoomMap rows according to per-room breakdown and mark rooms available
    for rid, amt in per_room_refunds.items():
        rmap = RefundRoomMap(refund_id=rf.refund_id, booking_id=booking.booking_id, room_id=rid, refund_amount=amt)
        db.add(rmap)
        q = await db.execute(select(Rooms).where(Rooms.room_id == rid))
        room = q.scalars().first()
        if room:
            room.room_status = 'AVAILABLE'

    # If full cancellation, mark booking-room mappings as inactive
    if full_cancel:
        for b in brm_items:
            b.is_room_active = False


    # Update booking status to Cancelled
    booking.status = 'Cancelled'
    db.add(booking)

    # commit transaction
    await db.commit()

    # reload and return refund
    stmt = select(Refunds).where(Refunds.refund_id == rf.refund_id)
    res = await db.execute(stmt)
    return res.scalars().first()


async def update_refund_transaction(db: AsyncSession, refund_id: int, payload, admin_user):
    """Admin may only update status, transaction_method_id and transaction_number.

    - If status is set to 'PROCESSED', set processed_at.
    - If status is set to 'COMPLETED', set processed_at and completed_at.
    """
    # Only admin will call this — caller should be validated by route dependency
    res = await db.execute(select(Refunds).where(Refunds.refund_id == refund_id))
    rf = res.scalars().first()
    if not rf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")

    data = payload.model_dump() if hasattr(payload, 'model_dump') else dict(payload)

    # Only allow specific fields
    status_val = data.get('status')
    method_id = data.get('transaction_method_id')
    trans_num = data.get('transaction_number')

    # Validate payment method if provided
    if method_id is not None:
        q = await db.execute(select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == method_id))
        pm = q.scalars().first()
        if not pm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction_method_id")
        rf.transaction_method_id = method_id

    if trans_num is not None:
        rf.transaction_number = trans_num

    if status_val is not None:
        rf.status = status_val
        now = datetime.utcnow()
        if status_val.upper() == 'PROCESSED':
            rf.processed_at = now
        if status_val.upper() == 'COMPLETED':
            rf.processed_at = now
            rf.completed_at = now

    db.add(rf)
    await db.commit()

    stmt = select(Refunds).where(Refunds.refund_id == refund_id)
    res = await db.execute(stmt)
    return res.scalars().first()


async def get_refund(db: AsyncSession, refund_id: int):
    """Retrieve a single refund by id or raise 404 if not found."""
    res = await db.execute(select(Refunds).where(Refunds.refund_id == refund_id))
    rf = res.scalars().first()
    if not rf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    return rf


async def list_refunds(db: AsyncSession, refund_id: int | None = None, booking_id: int | None = None, user_id: int | None = None, status: str | None = None, type: str | None = None, from_date: datetime | None = None, to_date: datetime | None = None):
    """Return a list of refunds filtered by the provided optional criteria.

    If refund_id is provided, this will return a list with that single refund (or empty if not found).
    """
    stmt = select(Refunds)
    # Build filters
    if refund_id is not None:
        stmt = stmt.where(Refunds.refund_id == refund_id)
    if booking_id is not None:
        stmt = stmt.where(Refunds.booking_id == booking_id)
    if user_id is not None:
        stmt = stmt.where(Refunds.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Refunds.status == status)
    if type is not None:
        stmt = stmt.where(Refunds.type == type)
    if from_date is not None:
        stmt = stmt.where(Refunds.initiated_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Refunds.initiated_at <= to_date)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return items
