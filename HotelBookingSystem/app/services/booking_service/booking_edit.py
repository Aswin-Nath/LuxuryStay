from datetime import datetime,timedelta
from fastapi import HTTPException, status
from sqlalchemy import select,delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingEdits, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms
from app.schemas.pydantic_models.booking_edits import BookingEditCreate, BookingEditResponse,ReviewPayload,DecisionPayload
from decimal import Decimal

# ✅ Create Booking Edit
async def create_booking_edit_service(payload: BookingEditCreate, db: AsyncSession, current_user) -> BookingEditResponse:
    stmt = select(Bookings).where(Bookings.booking_id == payload.booking_id)
    res = await db.execute(stmt)
    booking = res.scalars().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    now = datetime.utcnow()
    edit_type = payload.edit_type or ("POST" if now.date() >= booking.check_in else "PRE")

    # room_id:[room_type_id] this is for wanted rooms
    new_edit = BookingEdits(
        booking_id=payload.booking_id,
        user_id=payload.user_id,
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
        requested_by=payload.requested_by or current_user.user_id,
        requested_room_changes=payload.requested_room_changes or None,
    )

    async with db.begin():
        db.add(new_edit)

    await db.refresh(new_edit)
    return BookingEditResponse.model_validate(new_edit)


# ✅ Get Active Booking Edit
async def get_active_booking_edit_service(booking_id: int, db: AsyncSession):
    stmt = (
        select(BookingEdits)
        .where(
            BookingEdits.booking_id == booking_id,
            BookingEdits.edit_status.in_(["PENDING", "AWAITING_CUSTOMER_RESPONSE"]),
            BookingEdits.is_deleted == False,
        )
        .order_by(BookingEdits.requested_at.desc())
    )
    res = await db.execute(stmt)
    edit = res.scalars().first()
    return BookingEditResponse.model_validate(edit) if edit else None


# ✅ Get All Booking Edits
async def get_all_booking_edits_service(booking_id: int, db: AsyncSession):
    stmt = (
        select(BookingEdits)
        .where(BookingEdits.booking_id == booking_id, BookingEdits.is_deleted == False)
        .order_by(BookingEdits.requested_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [BookingEditResponse.model_validate(r) for r in rows]

# -----------------------
# Admin: suggest rooms & lock edit
# -----------------------
async def review_booking_edit_service(edit_id: int, payload: ReviewPayload, db: AsyncSession, current_user):
    # fetch edit
    stmt = select(BookingEdits).where(BookingEdits.edit_id == edit_id, BookingEdits.is_deleted == False)
    res = await db.execute(stmt)
    edit = res.scalars().first()
    if not edit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit not found")

    # Build lock expiry and suggested mapping
    lock_expires_at = datetime.utcnow() + timedelta(minutes=30)
    suggested = payload.suggested_rooms or {}

    # Persist changes: update booking_room_map rows' edit_suggested_rooms
    # Assume keys in suggested are either room_id or room_type_id; coerce to int
    q = await db.execute(select(BookingRoomMap).where(BookingRoomMap.booking_id == edit.booking_id))
    br_rows = q.scalars().all()

    # Update matching booking_room_map rows in-memory
    modified = False
    for key_str, room_ids in suggested.items():
        try:
            key = int(key_str)
        except Exception:
            # skip invalid keys
            continue
        for br in br_rows:
            # match either by room_id or room_type_id (flexible)
            if getattr(br, "room_id", None) == key == key:
                br.edit_suggested_rooms = room_ids
                db.add(br)
                modified = True

    # Update edit record
    edit.reviewed_by = current_user.user_id
    edit.edit_status = "AWAITING_CUSTOMER_RESPONSE"
    edit.lock_expires_at = lock_expires_at
    db.add(edit)

    # Flush + commit (no nested transactions)
    await db.flush()
    await db.commit()

    return {"ok": True, "edit_id": edit_id, "lock_expires_at": lock_expires_at.isoformat()}












async def decision_on_booking_edit_service(edit_id: int, payload: DecisionPayload, db: AsyncSession, current_user):
    """
    Handles customer decisioning on booking edits.
    - ACCEPT → replace with new room_id in booking_room_map, mark edited flag.
    - KEEP   → retain existing room.
    - REFUND → create refund + delete old room entry.
    """

    # 1️⃣ Fetch edit record
    stmt = select(BookingEdits).where(
        BookingEdits.edit_id == edit_id, BookingEdits.is_deleted == False
    )
    res = await db.execute(stmt)
    edit = res.scalars().first()
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")

    # 2️⃣ Permission check
    if current_user.user_id != edit.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized to act on this edit")

    # 3️⃣ Fetch booking & room maps
    q = await db.execute(select(Bookings).where(Bookings.booking_id == edit.booking_id))
    booking = q.scalars().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    q2 = await db.execute(select(BookingRoomMap).where(BookingRoomMap.booking_id == edit.booking_id))
    all_maps = q2.scalars().all()
    if not all_maps:
        raise HTTPException(status_code=404, detail="No room mappings found")

    # 4️⃣ Parse user decisions
    room_decisions = payload.room_decisions or {}
    affected_room_map_ids = set(map(int, room_decisions.keys()))

    accepted_rooms, kept_rooms, refund_rooms = [], [], []
    is_pre_edit = edit.edit_type == "PRE"
    is_post_edit = edit.edit_type == "POST"

    # 5️⃣ Apply user-level decisions
    for br in all_maps:
        if br.room_id not in affected_room_map_ids:
            continue

        decision, decision_room_id = room_decisions[br.room_id]

        # --- ACCEPT CASE ---
        if decision == "ACCEPT":
            accepted_rooms.append((br.room_id, decision_room_id))

            # 1. Delete existing (booking_id, old_room_id)
            await db.execute(
                delete(BookingRoomMap).where(
                    BookingRoomMap.booking_id == booking.booking_id,
                    BookingRoomMap.room_id == br.room_id
                )
            )

            # 2. Insert new (booking_id, new_room_id)

            # Determine room_type_id by querying the Rooms table for the accepted room
            room_type_id = None
            try:
                q_room = await db.execute(select(Rooms).where(Rooms.room_id == decision_room_id))
                room_obj = q_room.scalars().first()
                if room_obj:
                    room_type_id = room_obj.room_type_id
            except Exception:
                # leave room_type_id as None and fallback below
                room_type_id = None

            # Fallback: if we couldn't fetch room_type from Rooms, use the original mapping's type
            if room_type_id is None:
                room_type_id = getattr(br, "room_type_id", None)

            new_room_entry = BookingRoomMap(
                booking_id=booking.booking_id,
                room_type_id=room_type_id,
                room_id=decision_room_id,
                is_pre_edited_room=is_pre_edit,
                is_post_edited_room=is_post_edit,
            )

            db.add(new_room_entry)

        # --- KEEP CASE ---
        elif decision == "KEEP":
            kept_rooms.append(br.room_id)
            # no changes to DB (room kept as-is)
            continue

        # --- REFUND CASE ---
        elif decision == "REFUND":
            refund_rooms.append(br.room_id)

            total_rooms = max(len(all_maps), 1)
            try:
                per_room_amount = (Decimal(str(booking.total_price)) / Decimal(total_rooms)).quantize(Decimal("0.01"))
            except Exception:
                per_room_amount = Decimal("0.00")

            # Create refund record
            refund = Refunds(
                booking_id=booking.booking_id,
                user_id=current_user.user_id,
                type="PARTIAL",
                refund_amount=per_room_amount,
            )
            db.add(refund)
            await db.flush()

            # Link refund to room
            refund_room_map = RefundRoomMap(
                refund_id=refund.refund_id,
                booking_id=booking.booking_id,
                room_id=br.room_id,
                refund_amount=per_room_amount,
            )
            db.add(refund_room_map)

            # Delete refunded room
            await db.execute(
                delete(BookingRoomMap).where(
                    BookingRoomMap.booking_id == booking.booking_id,
                    BookingRoomMap.room_id == br.room_id
                )
            )

    # 6️⃣ Update edit status
    if accepted_rooms or refund_rooms:
        edit.edit_status = "PARTIALLY_APPROVED"
    elif kept_rooms:
        edit.edit_status = "NO_CHANGE"
    else:
        edit.edit_status = "REJECTED"

    edit.processed_at = datetime.utcnow()
    db.add(edit)

    # 7️⃣ Update booking flags
    if (accepted_rooms or refund_rooms) and booking:
        if is_pre_edit:
            booking.is_pre_edit_done = True
        elif is_post_edit:
            booking.is_post_edit_done = True
        db.add(booking)

    # 8️⃣ Commit
    await db.commit()

    # 9️⃣ Response payload
    return {
        "ok": True,
        "edit_id": edit_id,
        "status": edit.edit_status,
        "accepted_rooms": accepted_rooms,
        "kept_rooms": kept_rooms,
        "refund_rooms": refund_rooms,
        "message": f"Processed room-level decisions for edit #{edit_id}"
    }
