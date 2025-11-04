from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime

from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.models.sqlalchemy_schemas.rooms import Rooms
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

    full_cancel = bool(data.get('full_cancellation', False))

    # Determine refund amount
    if full_cancel:
        refund_amount = booking.total_price
    else:
        # partial: client must provide refund_amount or refund_rooms (and refund_amount)
        refund_amount = data.get('refund_amount')
        if refund_amount is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refund_amount is required for partial cancellations")
        refund_amount = Decimal(str(refund_amount))

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

    # If refund_rooms provided, create mapping rows and mark rooms available
    refund_rooms = data.get('refund_rooms') or []
    if refund_rooms:
        # If refund_amount provided, split equally among rooms
        per_room_amount = None
        if refund_amount is not None and len(refund_rooms) > 0:
            per_room_amount = (refund_amount / Decimal(len(refund_rooms))).quantize(Decimal('0.01'))
        for rid in refund_rooms:
            rmap = RefundRoomMap(refund_id=rf.refund_id, booking_id=booking.booking_id, room_id=rid, refund_amount=per_room_amount or Decimal('0'))
            db.add(rmap)
            # mark room available
            q = await db.execute(select(Rooms).where(Rooms.room_id == rid))
            room = q.scalars().first()
            if room:
                room.room_status = 'AVAILABLE'

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
