from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# CRUD imports
from app.crud.edit_bookings import (
    get_booking_by_id,
    create_booking_edit,
    get_booking_edit_by_id,
    list_booking_edits_for_booking,
    update_booking_edit_status,
    get_booking_room_maps,
    insert_booking_room_map,
    delete_booking_room_map,
    create_refund,
    create_refund_room_map,
    get_room_by_id,
    lock_room,
    unlock_room,
    update_booking_flags,
)

# Models & Schemas
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingEdits, BookingRoomMap
from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus, RoomTypes
from app.schemas.pydantic_models.booking_edits import (
    BookingEditCreate,
    BookingEditResponse,
    ReviewPayload,
    DecisionPayload,
)


# ✅ Create Booking Edit
async def create_booking_edit_service(payload: BookingEditCreate, db: AsyncSession, current_user) -> BookingEditResponse:
    booking = await get_booking_by_id(db, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Calculate edit_type dynamically based on original booking check-in date
    now = datetime.utcnow().date()
    edit_type = "POST" if now >= booking.check_in else "PRE"

    # ========== VALIDATION: Check for existing pending edits ==========
    existing_edits = await list_booking_edits_for_booking(db, payload.booking_id)
    pending_edits = [e for e in existing_edits if getattr(e, "edit_status", None) == "PENDING"]
    if pending_edits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking already has a pending edit. Please wait for it to be reviewed before making another edit."
        )

    # ========== VALIDATION: Room changes only allowed during PRE-EDIT ==========
    if payload.requested_room_changes and edit_type == "POST":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room changes are only allowed during PRE-EDIT phase (before check-in)"
        )

    # ========== VALIDATION: Date changes not allowed, only room changes in PRE-EDIT ==========

    
    # In POST-EDIT phase, no room changes or date changes allowed
    if edit_type == "POST":
        if payload.requested_room_changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room changes are not allowed after check-in (POST-EDIT phase)"
            )
        if payload.check_in_date or payload.check_out_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date changes are not allowed after check-in (POST-EDIT phase)"
            )

    # ========== CALCULATE TOTAL PRICE (only for room changes in PRE-EDIT) ==========
    calculated_total_price = Decimal(str(booking.total_price))
    
    if payload.requested_room_changes and edit_type == "PRE":
        # Get number of nights
        num_nights = max((booking.check_out - booking.check_in).days, 1)
        
        # Fetch all room types that will be used
        requested_room_type_ids = list(payload.requested_room_changes.values())  # new room_type_ids
        current_room_ids = list(payload.requested_room_changes.keys())  # current room_ids
        
        # Get room type prices for new rooms
        if requested_room_type_ids:
            query = await db.execute(
                select(RoomTypes).where(RoomTypes.room_type_id.in_(requested_room_type_ids))
            )
            new_room_types = {rt.room_type_id: rt for rt in query.scalars().all()}
        else:
            new_room_types = {}
        
        # Get current room prices for rooms being replaced
        if current_room_ids:
            query = await db.execute(
                select(Rooms).where(Rooms.room_id.in_(current_room_ids))
            )
            current_rooms = {r.room_id: r for r in query.scalars().all()}
        else:
            current_rooms = {}
        
        # Calculate cost differences
        total_cost_difference = Decimal("0")
        
        for current_room_id, new_room_type_id in payload.requested_room_changes.items():
            # Get old room price and new room type price
            old_room = current_rooms.get(current_room_id)
            new_room_type = new_room_types.get(new_room_type_id)
            
            if old_room and new_room_type:
                # Old room cost = room.price_per_night * num_nights
                old_cost = Decimal(str(old_room.price_per_night)) * Decimal(num_nights)
                # New room cost = room_type.price_per_night * num_nights
                new_cost = Decimal(str(new_room_type.price_per_night)) * Decimal(num_nights)
                # Difference = new_cost - old_cost
                difference = new_cost - old_cost
                total_cost_difference += difference
        
        # Final total_price = original_total_price + difference
        calculated_total_price = calculated_total_price + total_cost_difference
        calculated_total_price = float(calculated_total_price.quantize(Decimal("0.01")))

    # Only set fields that are provided (not None) - keep existing values for unchanged fields
    # All optional fields fall back to booking values if not provided in payload
    # Note: check_in_time and check_out_time are optional - only set if explicitly provided by user
    # (don't convert from booking's Time objects to datetime, keep them as-is)
    new_edit = BookingEdits(
        booking_id=payload.booking_id,
        user_id=current_user.user_id,
        primary_customer_name=payload.primary_customer_name or booking.primary_customer_name,
        primary_customer_phno=payload.primary_customer_phno or booking.primary_customer_phone_number,
        primary_customer_dob=payload.primary_customer_dob or booking.primary_customer_dob,
        check_in_date=booking.check_in,
        check_out_date=booking.check_out,
        check_in_time=payload.check_in_time,
        check_out_time=payload.check_out_time,
        total_price=calculated_total_price,
        edit_type=edit_type,
        edit_status="PENDING",
        requested_by=payload.requested_by or getattr(current_user, "user_id", None),
        requested_room_changes=payload.requested_room_changes if edit_type == "PRE" else None,
    )

    created_edit = await create_booking_edit(db, new_edit)
    await db.commit()
    return BookingEditResponse.model_validate(created_edit)


# ✅ Get All Booking Edits
async def get_all_booking_edits_service(booking_id: int, db: AsyncSession):
    edits = await list_booking_edits_for_booking(db, booking_id)
    return [BookingEditResponse.model_validate(e) for e in edits]


# ✅ Admin: Review Booking Edit & Lock
async def review_booking_edit_service(edit_id: int, payload: ReviewPayload, db: AsyncSession, current_user):
    edit = await get_booking_edit_by_id(db, edit_id)
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")

    lock_expires_at = datetime.utcnow() + timedelta(minutes=30)
    suggested = payload.suggested_rooms or {}

    room_maps = await get_booking_room_maps(db, edit.booking_id)
    for key_str, room_ids in suggested.items():
        key = int(key_str)
        for room_booking_map in room_maps:
            if getattr(room_booking_map, "room_id") == key:
                room_booking_map.edit_suggested_rooms = room_ids
                db.add(room_booking_map)

    await update_booking_edit_status(
        db,
        edit_id,
        status_value="AWAITING_CUSTOMER_RESPONSE",
        reviewed_by=current_user.user_id,
        lock_expires_at=lock_expires_at,
    )

    await db.commit()
    return {"ok": True, "edit_id": edit_id, "lock_expires_at": lock_expires_at.isoformat()}


# ✅ Customer Decision on Booking Edit
async def decision_on_booking_edit_service(edit_id: int, payload: DecisionPayload, db: AsyncSession, current_user):
    edit = await get_booking_edit_by_id(db, edit_id)
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")

    if current_user.user_id != edit.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized to act on this edit")

    booking = await get_booking_by_id(db, edit.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    room_maps = await get_booking_room_maps(db, edit.booking_id)
    if not room_maps:
        raise HTTPException(status_code=404, detail="No room mappings found")

    room_decisions = payload.room_decisions or {}
    affected_room_map_ids = set(map(int, room_decisions.keys()))

    accepted_rooms, kept_rooms, refund_rooms = [], [], []
    is_pre_edit = edit.edit_type == "PRE"
    is_post_edit = edit.edit_type == "POST"
    
    # Accumulate refund amounts for all rooms being refunded
    total_refund_amount = Decimal("0")
    per_room_refunds = {}  # Store individual room refund amounts

    for room_booking_map in room_maps:
        if room_booking_map.room_id not in affected_room_map_ids:
            continue

        decision, decision_room_id = room_decisions[room_booking_map.room_id]

        # --- ACCEPT CASE ---
        if decision == "ACCEPT":
            accepted_rooms.append((room_booking_map.room_id, decision_room_id))
            await delete_booking_room_map(db, booking.booking_id, room_booking_map.room_id)

            # Fetch new room details
            room_record = await get_room_by_id(db, decision_room_id)
            room_type_id = getattr(room_record, "room_type_id", getattr(room_booking_map, "room_type_id", None))

            new_map = BookingRoomMap(
                booking_id=booking.booking_id,
                room_type_id=room_type_id,
                room_id=decision_room_id,
                is_pre_edited_room=is_pre_edit,
                is_post_edited_room=is_post_edit,
            )
            await insert_booking_room_map(db, new_map)

        # --- KEEP CASE ---
        elif decision == "KEEP":
            kept_rooms.append(room_booking_map.room_id)
            continue

        # --- REFUND CASE ---
        elif decision == "REFUND":
            # Only refunds allowed in PRE-EDIT phase
            if not is_pre_edit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refunds are only allowed during PRE-EDIT phase (before check-in)"
                )
            
            refund_rooms.append(room_booking_map.room_id)
            
            # Calculate refund for this individual room: (CURRENT_DATE - BOOKING_DATE) × ROOM_PRICE_PER_NIGHT
            days_since_booking = max((datetime.utcnow().date() - booking.created_at.date()).days, 0)
            
            # Get the room details to get its price per night
            room_record = await get_room_by_id(db, room_booking_map.room_id)
            room_price_per_night = Decimal(str(room_record.price_per_night))
            room_refund_amount = (Decimal(days_since_booking) * room_price_per_night).quantize(Decimal("0.01"))
            
            # Store individual room refund amount
            per_room_refunds[room_booking_map.room_id] = room_refund_amount
            # Accumulate total refund
            total_refund_amount += room_refund_amount
            
            # Delete room from booking
            await delete_booking_room_map(db, booking.booking_id, room_booking_map.room_id)

    # Create single Refund record with total amount (only if there are refunds)
    if refund_rooms:
        refund = Refunds(
            booking_id=booking.booking_id,
            user_id=current_user.user_id,
            type="PARTIAL",
            refund_amount=total_refund_amount,
        )
        refund = await create_refund(db, refund)
        
        # Create individual RefundRoomMap entries for each refunded room
        for room_id, refund_amount in per_room_refunds.items():
            refund_room_map = RefundRoomMap(
                refund_id=refund.refund_id,
                booking_id=booking.booking_id,
                room_id=room_id,
                refund_amount=refund_amount,
            )
            await create_refund_room_map(db, refund_room_map)

    # Determine edit status
    if accepted_rooms or refund_rooms:
        edit_status = "APPROVED"
    elif kept_rooms:
        edit_status = "NO_CHANGE"
    else:
        edit_status = "REJECTED"

    edit.edit_status = edit_status
    edit.processed_at = datetime.utcnow()
    db.add(edit)

    if (accepted_rooms or refund_rooms) and booking:
        await update_booking_flags(db, booking, is_pre_edit=is_pre_edit, is_post_edit=is_post_edit)

    await db.commit()

    # Calculate new rooms amount (for accepted rooms)
    new_rooms_amount = Decimal("0")
    if accepted_rooms:
        # Recalculate total price based on new rooms if any were accepted
        # For now, we'll use the edit's calculated total_price if it was updated
        new_rooms_amount = Decimal(str(edit.total_price or booking.total_price))

    # Calculate new total amount after refunds and room changes
    original_booking_amount = Decimal(str(booking.total_price))
    refunded_amount = total_refund_amount
    new_total_amount = original_booking_amount - refunded_amount + (new_rooms_amount - original_booking_amount if accepted_rooms else Decimal("0"))

    return {
        "ok": True,
        "edit_id": edit_id,
        "status": edit_status,
        "financial_breakdown": {
            "original_booking_amount": float(original_booking_amount),
            "refunded_amount": float(refunded_amount),
            "new_rooms_amount": float(new_rooms_amount) if accepted_rooms else float(original_booking_amount),
            "new_total_amount": float(new_total_amount.quantize(Decimal("0.01"))),
        },
        "room_decisions": {
            "accepted_rooms": accepted_rooms,
            "kept_rooms": kept_rooms,
            "refund_rooms": refund_rooms,
        },
        "message": f"Processed room-level decisions for edit #{edit_id}",
    }


# ✅ Room Lock/Unlock Wrappers
async def lock_room_service(db: AsyncSession, room_id: int):
    room = await lock_room(db, room_id)
    await db.commit()
    return room


async def unlock_room_service(db: AsyncSession, room_id: int):
    room = await unlock_room(db, room_id)
    await db.commit()
    return room


async def change_room_status(db: AsyncSession, room_id: int, lock_flag: bool):
    if lock_flag:
        return await lock_room_service(db, room_id)
    return await unlock_room_service(db, room_id)


# ✅ Update Room Occupancy (Adults/Children) - No Admin Required
async def update_room_occupancy_service(
    booking_id: int,
    room_occupancy_updates: dict,
    db: AsyncSession,
    current_user
) -> list:
    """
    Update occupancy (adults and children count) for rooms in a booking.
    
    Allows customers to directly update room occupancy without admin approval.
    Validates that:
    - User owns the booking
    - Each room has at least 1 adult
    - Adults and children values are non-negative
    
    Args:
        booking_id (int): The booking ID to update occupancy for.
        room_occupancy_updates (dict): Dictionary with "room_updates" key containing list of updates.
            Format: {
                "room_updates": [
                    {"room_id": 101, "adults": 2, "children": 1},
                    {"room_id": 102, "adults": 1, "children": 0}
                ]
            }
        db (AsyncSession): Database session.
        current_user: Current authenticated user (must be booking owner).
    
    Returns:
        list: List of updated BookingRoomMap objects.
    
    Raises:
        HTTPException (403): If user is not the booking owner.
        HTTPException (404): If booking not found.
        HTTPException (404): If room_id not found in booking.
        HTTPException (400): If room has 0 adults.
        HTTPException (400): If adults or children are negative.
    """
    # ========== VALIDATION: Check booking exists and user owns it ==========
    booking = await get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update occupancy for your own bookings"
        )
    
    # ========== VALIDATION: Get all rooms in booking ==========
    booking_rooms = await get_booking_room_maps(db, booking_id)
    booking_room_ids = {room.room_id for room in booking_rooms}
    
    # ========== EXTRACT AND VALIDATE ROOM UPDATES ==========
    room_updates = room_occupancy_updates.get("room_updates", [])
    
    if not room_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No room updates provided. Expected: {'room_updates': [{'room_id': ..., 'adults': ..., 'children': ...}]}"
        )
    
    updated_rooms = []
    
    for update in room_updates:
        room_id = update.get("room_id")
        adults = update.get("adults")
        children = update.get("children")
        
        # Validate room_id exists in booking
        if room_id not in booking_room_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room ID {room_id} not found in booking {booking_id}"
            )
        
        # Validate adults is provided
        if adults is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id}: 'adults' field is required"
            )
        
        # Validate adults >= 1 (minimum 1 adult per room)
        if not isinstance(adults, int) or adults < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id}: Each room must have at least 1 adult. Got {adults}"
            )
        
        # Validate children is non-negative
        if children is None:
            children = 0
        
        if not isinstance(children, int) or children < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id}: Children count cannot be negative. Got {children}"
            )
        
        # ========== UPDATE ROOM OCCUPANCY ==========
        room_to_update = next((r for r in booking_rooms if r.room_id == room_id), None)
        if room_to_update:
            room_to_update.adults = adults
            room_to_update.children = children
            db.add(room_to_update)
            updated_rooms.append(room_to_update)
    
    # Commit all updates
    await db.commit()
    
    # Return updated rooms
    return updated_rooms
