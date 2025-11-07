from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.refund_management.refunds import (
    fetch_booking_by_id,
    fetch_refund_by_id,
    fetch_room_by_id,
    fetch_booking_room_maps,
    insert_refund_record,
    insert_refund_room_map,
    fetch_refunds_filtered,
)
from app.models.sqlalchemy_schemas.refunds import Refunds
from app.models.sqlalchemy_schemas.rooms import RoomStatus
from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility


async def cancel_booking_and_create_refund(db: AsyncSession, booking_id: int, payload, current_user):
    booking = await fetch_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot cancel a booking you do not own")

    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    refund_rooms = data.get("refund_rooms") or []
    full_cancel = bool(data.get("full_cancellation", False)) or (len(refund_rooms) == 0)

    nights = max((booking.check_out - booking.check_in).days, 1)
    brm_items = await fetch_booking_room_maps(db, booking.booking_id)
    brm_by_room = {b.room_id: b for b in brm_items}

    async def compute_room_total(room_id: int) -> Decimal:
        room = await fetch_room_by_id(db, room_id)
        if not room:
            return Decimal("0")
        return (Decimal(str(room.price_per_night)) * Decimal(nights)).quantize(Decimal("0.01"))

    per_room_refunds = {}
    if full_cancel:
        refund_amount = Decimal(str(booking.total_price))
        for b in brm_items:
            per_room_refunds[b.room_id] = await compute_room_total(b.room_id)
    else:
        if not refund_rooms:
            raise HTTPException(status_code=400, detail="refund_rooms required for partial cancellations")
        total = Decimal("0")
        for rid in refund_rooms:
            amt = await compute_room_total(rid)
            per_room_refunds[rid] = amt
            total += amt
        refund_amount = total.quantize(Decimal("0.01"))

    rf_data = dict(
        booking_id=booking.booking_id,
        user_id=current_user.user_id,
        type="CANCELLATION" if full_cancel else "PARTIAL_CANCEL",
        status="INITIATED",
        refund_amount=refund_amount,
        remarks=data.get("remarks"),
        transaction_method_id=data.get("transaction_method_id"),
        transaction_number=data.get("transaction_number"),
    )

    rf = await insert_refund_record(db, rf_data)

    # Create refund room maps
    for rid, amt in per_room_refunds.items():
        await insert_refund_room_map(
            db,
            dict(refund_id=rf.refund_id, booking_id=booking.booking_id, room_id=rid, refund_amount=amt),
        )
        room = await fetch_room_by_id(db, rid)
        if room:
            room.room_status = "AVAILABLE"

    if full_cancel:
        for b in brm_items:
            b.is_room_active = False

    booking.status = "Cancelled"
    db.add(booking)
    await db.commit()

    refund = await fetch_refund_by_id(db, rf.refund_id)
    return refund


async def update_refund_transaction(db: AsyncSession, refund_id: int, payload, admin_user):
    rf = await fetch_refund_by_id(db, refund_id)
    if not rf:
        raise HTTPException(status_code=404, detail="Refund not found")

    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    status_val = data.get("status")
    method_id = data.get("transaction_method_id")
    trans_num = data.get("transaction_number")

    if method_id is not None:
        q = await db.execute(
            select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == method_id)
        )
        pm = q.scalars().first()
        if not pm:
            raise HTTPException(status_code=400, detail="Invalid transaction_method_id")
        rf.transaction_method_id = method_id

    if trans_num is not None:
        rf.transaction_number = trans_num

    if status_val is not None:
        rf.status = status_val
        now = datetime.utcnow()
        if status_val.upper() == "PROCESSED":
            rf.processed_at = now
        if status_val.upper() == "COMPLETED":
            rf.processed_at = now
            rf.completed_at = now

    db.add(rf)
    await db.commit()
    return rf


async def get_refund(db: AsyncSession, refund_id: int):
    refund = await fetch_refund_by_id(db, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund


async def list_refunds(db: AsyncSession, **filters):
    return await fetch_refunds_filtered(db, **filters)
