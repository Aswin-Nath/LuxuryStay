from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.refunds import (
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
    """
    Cancel booking and create refund record with optional partial cancellation.
    
    Creates a refund for a booking and releases allocated rooms back to AVAILABLE status.
    Supports full cancellation (all rooms) or partial cancellation (specific rooms).
    Calculates refund amount based on number of nights and per-room pricing.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        booking_id (int): The ID of the booking to cancel.
        payload: Pydantic model containing refund_rooms (list), full_cancellation (bool), remarks, transaction details.
        current_user: The authenticated user (must be booking owner for authorization).
    
    Returns:
        dict: Refund details including refund_id, booking_id, amount, status, rooms affected.
    
    Raises:
        HTTPException (404): If booking not found.
        HTTPException (403): If user doesn't own the booking.
        HTTPException (400): If partial cancellation attempted without specifying rooms.
    """
    booking = await fetch_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot cancel a booking you do not own")

    refund_payload = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    refund_rooms = refund_payload.get("refund_rooms") or []
    full_cancel = bool(refund_payload.get("full_cancellation", False)) or (len(refund_rooms) == 0)

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
        remarks=refund_payload.get("remarks"),
        transaction_method_id=None,
        transaction_number=None,
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
    """
    Update refund transaction details and status.
    
    Updates payment method, transaction number, and refund status. When status is set to PROCESSED
    or COMPLETED, sets corresponding timestamps automatically. Validates payment method exists.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        refund_id (int): The ID of the refund to update.
        payload: Pydantic model containing status, transaction_method_id, transaction_number fields.
        admin_user: The authenticated admin user performing the update.
    
    Returns:
        Refund: Updated refund record with new transaction details and status.
    
    Raises:
        HTTPException (404): If refund not found.
        HTTPException (400): If transaction_method_id is invalid or doesn't exist in PaymentMethodUtility.
    """
    refund_record = await fetch_refund_by_id(db, refund_id)
    if not refund_record:
        raise HTTPException(status_code=404, detail="Refund not found")

    refund_update_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    status_val = refund_update_data.get("status")
    method_id = refund_update_data.get("transaction_method_id")
    trans_num = refund_update_data.get("transaction_number")

    if method_id is not None:
        payment_method_query = await db.execute(
            select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == method_id)
        )
        payment_method = payment_method_query.scalars().first()
        if not payment_method:
            raise HTTPException(status_code=400, detail="Invalid transaction_method_id")
        refund_record.transaction_method_id = method_id

    if trans_num is not None:
        refund_record.transaction_number = trans_num

    if status_val is not None:
        refund_record.status = status_val
        now = datetime.utcnow()
        if status_val.upper() == "PROCESSED":
            refund_record.processed_at = now
        if status_val.upper() == "COMPLETED":
            refund_record.processed_at = now
            refund_record.completed_at = now

    db.add(refund_record)
    await db.commit()
    return refund_record


async def get_refund(db: AsyncSession, refund_id: int):
    """
    Retrieve refund record by ID.
    
    Fetches a single refund record with all related transaction details and room-level
    refund mappings.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        refund_id (int): The ID of the refund to retrieve.
    
    Returns:
        Refund: The refund record with all details including transaction info and room mappings.
    
    Raises:
        HTTPException (404): If refund with the given ID not found.
    """
    refund = await fetch_refund_by_id(db, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund


async def list_refunds(db: AsyncSession, **filters):
    """
    List refunds with optional filtering.
    
    Retrieves multiple refund records with support for filtering by status, user, booking,
    date range, and other criteria. Results include all transaction and room-level details.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        **filters: Optional filter parameters including:
            - status (str): Filter by refund status (e.g., INITIATED, PROCESSED, COMPLETED).
            - user_id (int): Filter by refund owner user ID.
            - booking_id (int): Filter by associated booking ID.
            - skip (int): Number of records to skip for pagination.
            - limit (int): Maximum number of records to return.
    
    Returns:
        list[Refund]: List of refund records matching the filter criteria with all details.
    """
    return await fetch_refunds_filtered(db, **filters)
