from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD imports
from app.crud.booking_management.edit_bookings import (
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
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus
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

    now = datetime.utcnow()
    edit_type = payload.edit_type or ("POST" if now.date() >= booking.check_in else "PRE")

    new_edit = BookingEdits(
        booking_id=payload.booking_id,
        user_id=getattr(current_user, "user_id", None),
        primary_customer_name=payload.primary_customer_name,
        primary_customer_phno=payload.primary_customer_phno,
        primary_customer_dob=payload.primary_customer_dob,
        check_in_date=payload.check_in_date,
        check_out_date=payload.check_out_date,
        check_in_time=payload.check_in_time,
        check_out_time=payload.check_out_time,
        total_price=payload.total_price,
        edit_type=edit_type,
        edit_status="PENDING",
        requested_by=payload.requested_by or getattr(current_user, "user_id", None),
        requested_room_changes=payload.requested_room_changes or None,
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
            refund_rooms.append(room_booking_map.room_id)
            total_rooms = max(len(room_maps), 1)
            try:
                per_room_amount = (Decimal(str(booking.total_price)) / Decimal(total_rooms)).quantize(Decimal("0.01"))
            except Exception:
                per_room_amount = Decimal("0.00")

            refund = Refunds(
                booking_id=booking.booking_id,
                user_id=current_user.user_id,
                type="PARTIAL",
                refund_amount=per_room_amount,
            )
            refund = await create_refund(db, refund)
            refund_room_map = RefundRoomMap(
                refund_id=refund.refund_id,
                booking_id=booking.booking_id,
                room_id=room_booking_map.room_id,
                refund_amount=per_room_amount,
            )
            await create_refund_room_map(db, refund_room_map)
            await delete_booking_room_map(db, booking.booking_id, room_booking_map.room_id)

    # Determine edit status
    if accepted_rooms or refund_rooms:
        edit_status = "PARTIALLY_APPROVED"
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

    return {
        "ok": True,
        "edit_id": edit_id,
        "status": edit_status,
        "accepted_rooms": accepted_rooms,
        "kept_rooms": kept_rooms,
        "refund_rooms": refund_rooms,
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
