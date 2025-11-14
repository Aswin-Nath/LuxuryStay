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
from app.crud.rooms import fetch_room_type_by_id
from app.models.sqlalchemy_schemas.refunds import Refunds
from app.models.sqlalchemy_schemas.rooms import RoomStatus
from app.models.sqlalchemy_schemas.payment_method import PaymentMethodUtility


async def cancel_booking_and_create_refund(db: AsyncSession, booking_id: int, current_user):
    """
    Cancel booking completely and create full refund record (INITIATED status).
    
    Performs a FULL immediate cancellation of the entire booking:
    - Releases ALL allocated rooms back to AVAILABLE status
    - Creates refund record for 100% of booking amount with INITIATED status
    - Marks booking as CANCELLED
    - Calculates per-room refund amounts based on number of nights and room pricing
    
    This function only supports complete booking cancellations and does NOT require a payload.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        booking_id (int): The ID of the booking to cancel completely.
        current_user: The authenticated user (must be booking owner for authorization).
    
    Returns:
        Refunds: The created refund record with INITIATED status, full refund amount, and all room mappings.
    
    Raises:
        HTTPException (404): If booking not found.
        HTTPException (403): If user doesn't own the booking.
        HTTPException (400): If booking is already cancelled.
    """
    # ========== FETCH & VALIDATE BOOKING ==========
    booking = await fetch_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    if booking.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel a booking you do not own"
        )

    if booking.status == "Cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking is already cancelled"
        )

    # ========== CALCULATE REFUND AMOUNT ==========
    # Full cancellation: refund 100% of booking total price
    total_refund_amount = Decimal(str(booking.total_price))
    
    number_of_nights = max((booking.check_out - booking.check_in).days, 1)
    booking_room_maps = await fetch_booking_room_maps(db, booking.booking_id)

    # ========== COMPUTE PER-ROOM REFUND AMOUNTS ==========
    per_room_refund_amounts = {}
    for booking_room_map in booking_room_maps:
        room = await fetch_room_by_id(db, booking_room_map.room_id)
        if room:
            # Get price from the room's type
            room_type = await fetch_room_type_by_id(db, room.room_type_id)
            if room_type:
                room_refund_amount = (
                    Decimal(str(room_type.price_per_night)) * Decimal(number_of_nights)
                ).quantize(Decimal("0.01"))
                per_room_refund_amounts[booking_room_map.room_id] = room_refund_amount

    # ========== CREATE REFUND RECORD WITH INITIATED STATUS ==========
    refund_record_data = {
        "booking_id": booking.booking_id,
        "user_id": current_user.user_id,
        "type": "CANCELLATION",
        "status": "INITIATED",
        "refund_amount": total_refund_amount,
        "remarks": f"Full booking cancellation initiated by user {current_user.user_id}",
        "transaction_method_id": None,
        "transaction_number": None,
    }

    refund_record = await insert_refund_record(db, refund_record_data)

    # ========== CREATE REFUND ROOM MAPPINGS & RELEASE ROOMS ==========
    for room_id, refund_amount in per_room_refund_amounts.items():
        # Create refund room map record
        await insert_refund_room_map(
            db,
            {
                "refund_id": refund_record.refund_id,
                "booking_id": booking.booking_id,
                "room_id": room_id,
                "refund_amount": refund_amount,
            },
        )
        
        # Release room back to AVAILABLE status
        room = await fetch_room_by_id(db, room_id)
        if room:
            room.room_status = RoomStatus.AVAILABLE

    # ========== DEACTIVATE ALL BOOKING ROOM MAPPINGS ==========
    for booking_room_map in booking_room_maps:
        booking_room_map.is_room_active = False

    # ========== UPDATE BOOKING STATUS TO CANCELLED ==========
    booking.status = "Cancelled"
    db.add(booking)
    
    # ========== COMMIT ALL CHANGES ATOMICALLY ==========
    await db.commit()

    # ========== RETRIEVE & RETURN REFUND RECORD ==========
    complete_refund_record = await fetch_refund_by_id(db, refund_record.refund_id)
    return complete_refund_record


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    update_payload_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    new_status = update_payload_data.get("status")
    payment_method_id = update_payload_data.get("transaction_method_id")
    transaction_number = update_payload_data.get("transaction_number")

    # ========== VALIDATE & UPDATE PAYMENT METHOD ==========
    if payment_method_id is not None:
        payment_method_query = await db.execute(
            select(PaymentMethodUtility).where(PaymentMethodUtility.method_id == payment_method_id)
        )
        payment_method_exists = payment_method_query.scalars().first()
        if not payment_method_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction_method_id"
            )
        refund_record.transaction_method_id = payment_method_id

    # ========== UPDATE TRANSACTION NUMBER ==========
    if transaction_number is not None:
        refund_record.transaction_number = transaction_number

    # ========== UPDATE STATUS & SET TIMESTAMPS ==========
    if new_status is not None:
        refund_record.status = new_status
        current_timestamp = datetime.utcnow()
        
        if new_status.upper() == "PROCESSED":
            refund_record.processed_at = current_timestamp
        
        if new_status.upper() == "COMPLETED":
            refund_record.processed_at = current_timestamp
            refund_record.completed_at = current_timestamp

    # ========== COMMIT CHANGES ==========
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
