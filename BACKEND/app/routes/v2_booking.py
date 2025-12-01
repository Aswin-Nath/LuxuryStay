from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime, timedelta

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomAvailabilityLocks, RoomTypes
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.payments import Payments
from app.crud.bookings import create_payment
import uuid

router = APIRouter(prefix="/v2/rooms", tags=["Room Availability Locking"])

# ==========================================================
# 📋 GET ALL ROOM TYPES (For dropdown/filter)
# ==========================================================
@router.get("/room-types")
async def get_all_room_types(db: AsyncSession = Depends(get_db)):
    """
    Get all available room types from database.
    Used for populating room type dropdown in search filters.
    
    Returns: List of all room types with full details
    """
    result = await db.execute(select(RoomTypes))
    room_types = result.scalars().all()

    return {
        "total": len(room_types),
        "results": [
            {
                "room_type_id": rt.room_type_id,
                "type_name": rt.type_name,
                "max_adult_count": rt.max_adult_count,
                "max_child_count": rt.max_child_count,
                "price_per_night": float(rt.price_per_night),
                "description": rt.description,
                "square_ft": rt.square_ft
            }
            for rt in room_types
        ]
    }


# ==========================================================
# 🔒 LOCK ROOM BY TYPE
# ==========================================================
@router.post("/lock")
async def lock_room(
    room_type_id: int = Body(...),
    check_in: str = Body(...),
    check_out: str = Body(...),
    expires_at: str = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Lock one AVAILABLE room from room_type for a date window.
    
    Returns consistent HTTP status codes:
    - 404: Room type doesn't exist (ROOM_TYPE_NOT_FOUND)
    - 409: No availability for selected dates (ROOM_UNAVAILABLE)
    - 423: Lock conflict (ROOM_LOCK_FAILED)
    
    Body:
    {
      "room_type_id": 2,
      "check_in": "2025-12-15",
      "check_out": "2025-12-18",
      "expires_at": "2025-12-01T14:30:00Z"
    }
    """
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD for dates and ISO 8601 for expires_at"
        )

    if check_in_date >= check_out_date:
        raise HTTPException(
            status_code=400,
            detail="check_in must be before check_out"
        )

    now = datetime.utcnow()

    # 1. Get room type details
    rt_result = await db.execute(
        select(RoomTypes).where(RoomTypes.room_type_id == room_type_id)
    )
    room_type = rt_result.scalar_one_or_none()
    
    if not room_type:
        raise HTTPException(
            status_code=404,
            detail=f"Room type with ID {room_type_id} does not exist",
        )

    # 2. Get all rooms in this type
    result = await db.execute(
        select(Rooms).where(Rooms.room_type_id == room_type_id)
    )
    rooms = result.scalars().all()

    if not rooms:
        # 409 Conflict: Room type exists but has no physical rooms (no availability)
        raise HTTPException(
            status_code=409,
            detail=f"No {room_type.type_name} rooms currently available. Please try another room type."
        )

    # 3. Find rooms already locked for this date window
    locked_result = await db.execute(
        select(RoomAvailabilityLocks.room_id)
        .where(RoomAvailabilityLocks.expires_at > now)
        .where(RoomAvailabilityLocks.check_in < check_out_date)
        .where(RoomAvailabilityLocks.check_out > check_in_date)
    )
    locked_ids = set(locked_result.scalars().all())

    # 4. Pick first free room
    free_room = next((r for r in rooms if r.room_id not in locked_ids), None)

    if not free_room:
        # 409 Conflict: No availability (user can retry with different dates)
        raise HTTPException(
            status_code=409,
            detail=f"No {room_type.type_name} rooms available for {check_in} to {check_out}"
        )

    # 5. Insert lock
    lock = RoomAvailabilityLocks(
        room_id=free_room.room_id,
        room_type_id=room_type_id,
        user_id=current_user.user_id,
        check_in=check_in_date,
        check_out=check_out_date,
        expires_at=expiry
    )
    db.add(lock)
    await db.commit()
    await db.refresh(lock)

    # Calculate number of nights for price calculation
    nights = (check_out_date - check_in_date).days

    return {
        "lock_id": lock.lock_id,
        "room_id": lock.room_id,
        "room_type_id": room_type_id,
        "type_name": room_type.type_name,
        "check_in": check_in_date.isoformat(),
        "check_out": check_out_date.isoformat(),
        "expires_at": lock.expires_at.isoformat(),
        "price_per_night": float(room_type.price_per_night),
        "nights": nights,
        "total_price": float(room_type.price_per_night) * nights,
        "room_no": free_room.room_no,
        "max_adult_count": room_type.max_adult_count,
        "max_child_count": room_type.max_child_count,
        "square_ft": room_type.square_ft,
        "description": room_type.description
    }


# ==========================================================
# 🔓 UNLOCK ROOM
# ==========================================================
@router.post("/unlock/{lock_id}")
async def unlock_room(
    lock_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Unlock a room by deleting its lock.
    Only the user who locked it can unlock.
    """
    result = await db.execute(
        select(RoomAvailabilityLocks).where(RoomAvailabilityLocks.lock_id == lock_id)
    )
    lock = result.scalar_one_or_none()

    if not lock:
        raise HTTPException(status_code=404, detail="Lock not found")

    if lock.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your lock")

    # Properly delete the lock
    await db.execute(
        delete(RoomAvailabilityLocks).where(RoomAvailabilityLocks.lock_id == lock_id)
    )
    await db.commit()

    return {"unlocked": True}


# ==========================================================
# 🔓 RELEASE ALL USER LOCKS (Date Change)
# ==========================================================
@router.post("/release-all-locks")
async def release_all_user_locks(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Release all locks for the current user.
    Used when dates are changed and all locks need to be cleared.
    """
    from sqlalchemy import delete
    
    # Delete all locks for this user
    result = await db.execute(
        delete(RoomAvailabilityLocks).where(
            RoomAvailabilityLocks.user_id == current_user.user_id
        )
    )
    
    locks_released = result.rowcount
    await db.commit()

    return {
        "success": True,
        "locks_released": locks_released,
        "message": f"Released {locks_released} room locks"
    }


# ==========================================================
# 📋 GET MY LOCKS
# ==========================================================
@router.get("/my-locks")
async def get_my_locks(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Get all non-expired locks for current user.
    """
    now = datetime.utcnow()

    result = await db.execute(
        select(RoomAvailabilityLocks)
        .where(RoomAvailabilityLocks.user_id == current_user.user_id)
        .where(RoomAvailabilityLocks.expires_at > now)
    )
    locks = result.scalars().all()

    return {
        "total": len(locks),
        "locks": [
            {
                "lock_id": l.lock_id,
                "room_id": l.room_id,
                "check_in": l.check_in.isoformat(),
                "check_out": l.check_out.isoformat(),
                "expires_at": l.expires_at.isoformat()
            }
            for l in locks
        ]
    }


# ==========================================================
# 🔍 SEARCH ROOMS (Date-Based, Room-Type Based with Filters)
# ==========================================================
@router.get("/search")
async def search_rooms(
    check_in: str,
    check_out: str,
    room_type_id: int = None,
    type_name: str = None,
    max_adult_count: int = None,
    max_child_count: int = None,
    price_per_night_min: float = None,
    price_per_night_max: float = None,
    square_ft_min: int = None,
    square_ft_max: int = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Search available rooms with multiple filter options.
    
    Required: check_in, check_out (YYYY-MM-DD)
    
    Optional filters from RoomTypes:
    - room_type_id: exact room type
    - type_name: room type name
    - max_adult_count: max adults
    - max_child_count: max children
    - price_per_night_min/max: price range
    - square_ft_min/max: size range
    
    Returns: matching room types with availability counts
    """
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")

    if check_in_date >= check_out_date:
        raise HTTPException(status_code=400, detail="check_in must be before check_out")

    now = datetime.utcnow()

    # Build room type filters
    room_type_filters = []
    if room_type_id:
        room_type_filters.append(RoomTypes.room_type_id == room_type_id)
    if type_name:
        room_type_filters.append(RoomTypes.type_name.ilike(f"%{type_name}%"))
    if max_adult_count:
        room_type_filters.append(RoomTypes.max_adult_count >= max_adult_count)
    if max_child_count is not None:
        room_type_filters.append(RoomTypes.max_child_count >= max_child_count)
    if price_per_night_min:
        room_type_filters.append(RoomTypes.price_per_night >= price_per_night_min)
    if price_per_night_max:
        room_type_filters.append(RoomTypes.price_per_night <= price_per_night_max)
    if square_ft_min:
        room_type_filters.append(RoomTypes.square_ft >= square_ft_min)
    if square_ft_max:
        room_type_filters.append(RoomTypes.square_ft <= square_ft_max)

    # Get matching room types
    room_type_query = select(RoomTypes)
    if room_type_filters:
        from sqlalchemy import and_
        room_type_query = room_type_query.where(and_(*room_type_filters))

    result = await db.execute(room_type_query)
    room_types = result.scalars().all()

    if not room_types:
        return {
            "total_types": 0,
            "results": []
        }

    # For each room type, calculate availability
    results = []
    for rt in room_types:
        # Get all rooms of this type
        rooms_result = await db.execute(
            select(Rooms.room_id).where(Rooms.room_type_id == rt.room_type_id)
        )
        all_ids = [r[0] for r in rooms_result.fetchall()]

        # Get locked rooms for overlapping dates
        lock_result = await db.execute(
            select(RoomAvailabilityLocks.room_id)
            .where(RoomAvailabilityLocks.expires_at > now)
            .where(RoomAvailabilityLocks.check_in < check_out_date)
            .where(RoomAvailabilityLocks.check_out > check_in_date)
            .where(RoomAvailabilityLocks.room_type_id == rt.room_type_id)
        )
        locked_ids = set(lock_result.scalars().all())

        free_count = len([rid for rid in all_ids if rid not in locked_ids])

        results.append({
            "room_type_id": rt.room_type_id,
            "type_name": rt.type_name,
            "max_adult_count": rt.max_adult_count,
            "max_child_count": rt.max_child_count,
            "price_per_night": float(rt.price_per_night),
            "description": rt.description,
            "square_ft": rt.square_ft,
            "total_rooms": len(all_ids),
            "locked_rooms": len(locked_ids),
            "free_rooms": free_count
        })

    return {
        "total_types": len(results),
        "check_in": check_in,
        "check_out": check_out,
        "results": results
    }


# ==========================================================
# 💰 BOOKING SUMMARY (Final Calculation Before Payment)
# ==========================================================
@router.get("/booking/summary")
async def get_booking_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Get booking summary with final calculations.
    Shows all locked rooms and total amount.
    """
    now = datetime.utcnow()

    # Get valid locks with room details
    result = await db.execute(
        select(RoomAvailabilityLocks, Rooms, RoomTypes)
        .join(Rooms, Rooms.room_id == RoomAvailabilityLocks.room_id)
        .join(RoomTypes, RoomTypes.room_type_id == Rooms.room_type_id)
        .where(RoomAvailabilityLocks.user_id == current_user.user_id)
        .where(RoomAvailabilityLocks.expires_at > now)
    )

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=400, detail="No active rooms locked")

    summary = []
    total = 0

    for lock, room, room_type in rows:
        nights = (lock.check_out - lock.check_in).days
        price = float(room_type.price_per_night) * nights
        total += price

        summary.append({
            "lock_id": lock.lock_id,
            "room_id": room.room_id,
            "room_no": room.room_no,
            "room_type": room_type.type_name,
            "check_in": lock.check_in.isoformat(),
            "check_out": lock.check_out.isoformat(),
            "nights": nights,
            "price_per_night": float(room_type.price_per_night),
            "price_total": price
        })

    return {
        "rooms": summary,
        "final_amount": total
    }


# ==========================================================
# ✅ CONFIRM BOOKING (Make Payment / Create Booking)
# ==========================================================
from app.schemas.pydantic_models.v2_booking_schemas import (
    BookingConfirmRequest,
    PaymentConfirmationResponse,
    BookingRoomDetail
)

@router.post("/booking/confirm", response_model=PaymentConfirmationResponse)
async def confirm_booking(
    request: BookingConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Confirm booking with guest details and process payment.
    Accepts guest details for each locked room and creates comprehensive booking.
    
    Body:
    {
      "payment_method_id": 1,  # 1=Card, 2=UPI, 3=NetBanking
      "rooms_guest_details": [
        {
          "lock_id": 123,
          "guest_name": "John Doe",
          "guest_age": 28,
          "adult_count": 2,
          "child_count": 1,
          "special_requests": "High floor"
        }
      ]
    }
    """
    now = datetime.utcnow()
    
    # Step 1: Get all locks specified in request
    lock_ids = [gd.lock_id for gd in request.rooms_guest_details]
    
    result = await db.execute(
        select(RoomAvailabilityLocks, Rooms, RoomTypes)
        .join(Rooms, Rooms.room_id == RoomAvailabilityLocks.room_id)
        .join(RoomTypes, RoomTypes.room_type_id == Rooms.room_type_id)
        .where(RoomAvailabilityLocks.lock_id.in_(lock_ids))
        .where(RoomAvailabilityLocks.user_id == current_user.user_id)
        .where(RoomAvailabilityLocks.expires_at > now)
    )

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=400, detail="No active rooms locked")

    if len(rows) != len(request.rooms_guest_details):
        raise HTTPException(status_code=400, detail="Mismatch between locked rooms and guest details")

    # Create mapping of lock_id to guest details for quick lookup
    guest_details_map = {gd.lock_id: gd for gd in request.rooms_guest_details}

    # Step 2: Get primary customer details from users table
    user = current_user
    
    # Step 3: Create booking entry
    # Get check_in and check_out from first lock
    first_lock = rows[0][0]
    booking = Bookings(
        user_id=current_user.user_id,
        room_count=len(rows),
        check_in=first_lock.check_in,
        check_out=first_lock.check_out,
        total_price=0,  # Will update after calculating
        status="Confirmed",
        created_at=now,
        primary_customer_name=user.full_name if hasattr(user, 'full_name') else None,
        primary_customer_phone_number=user.phone_number if hasattr(user, 'phone_number') else None,
        primary_customer_dob=user.dob if hasattr(user, 'dob') else None
    )
    db.add(booking)
    await db.flush()

    # Step 4: Map rooms to booking with guest details + Calculate total amount
    total_amount = 0.0
    booking_rooms_details = []
    
    for lock, room, room_type in rows:
        guest_detail = guest_details_map.get(lock.lock_id)
        if not guest_detail:
            raise HTTPException(status_code=400, detail=f"Missing guest details for lock {lock.lock_id}")

        nights = (lock.check_out - lock.check_in).days
        price = float(room_type.price_per_night) * nights
        total_amount += price

        # Create BookingRoomMap with guest details
        booking_room = BookingRoomMap(
            booking_id=booking.booking_id,
            room_id=room.room_id,
            room_type_id=room_type.room_type_id,
            guest_name=guest_detail.guest_name,
            guest_age=guest_detail.guest_age,
            special_requests=guest_detail.special_requests,
            updated_at=now,
            adults=guest_detail.adult_count,
            children=guest_detail.child_count
        )
        db.add(booking_room)

        # Store for response
        booking_rooms_details.append({
            "room_id": room.room_id,
            "room_no": room.room_no,
            "type_name": room_type.type_name,
            "check_in": lock.check_in,
            "check_out": lock.check_out,
            "nights": nights,
            "price_per_night": float(room_type.price_per_night),
            "total_price": price,
            "guest_name": guest_detail.guest_name,
            "guest_age": guest_detail.guest_age,
            "adult_count": guest_detail.adult_count,
            "child_count": guest_detail.child_count,
            "special_requests": guest_detail.special_requests
        })

    await db.flush()

    # Update booking total_price before creating payment
    booking.total_price = total_amount

    # Step 5: Calculate GST (18%)
    gst_amount = total_amount * 0.18
    final_amount = total_amount + gst_amount

    # Step 6: Create payment record
    transaction_reference = f"TXN_{booking.booking_id}_{uuid.uuid4().hex[:8].upper()}"
    payment = Payments(
        booking_id=booking.booking_id,
        amount=final_amount,
        method_id=request.payment_method_id,
        status="SUCCESS",
        transaction_reference=transaction_reference,
        user_id=current_user.user_id,
        remarks=f"Payment for booking #{booking.booking_id} - {len(rows)} room(s)"
    )
    db.add(payment)
    await db.flush()

    # Step 7: Delete locks
    await db.execute(
        delete(RoomAvailabilityLocks).where(
            RoomAvailabilityLocks.lock_id.in_(lock_ids)
        )
    )

    await db.commit()

    # Get payment method name
    payment_methods = {1: "Credit/Debit Card", 2: "UPI", 3: "Net Banking"}
    payment_method_name = payment_methods.get(request.payment_method_id, "Unknown")

    # Return comprehensive confirmation
    return PaymentConfirmationResponse(
        booking_id=booking.booking_id,
        user_id=current_user.user_id,
        check_in=first_lock.check_in,
        check_out=first_lock.check_out,
        total_nights=sum((lock.check_out - lock.check_in).days for lock, _, _ in rows),
        booking_status="CONFIRMED",
        created_at=now,
        rooms=[
            BookingRoomDetail(
                room_id=detail["room_id"],
                room_no=detail["room_no"],
                type_name=detail["type_name"],
                check_in=detail["check_in"],
                check_out=detail["check_out"],
                nights=detail["nights"],
                price_per_night=detail["price_per_night"],
                total_price=detail["total_price"],
                guest_name=detail["guest_name"],
                guest_age=detail["guest_age"],
                adult_count=detail["adult_count"],
                child_count=detail["child_count"],
                special_requests=detail["special_requests"]
            )
            for detail in booking_rooms_details
        ],
        room_count=len(rows),
        subtotal=total_amount,
        gst_18_percent=gst_amount,
        total_amount=final_amount,
        payment_id=payment.payment_id,
        payment_status="SUCCESS",
        payment_method=payment_method_name,
        transaction_reference=transaction_reference,
        transaction_date=now
    )


# ==========================================================
# 📋 BOOKING SESSION MANAGEMENT (15-MINUTE WINDOW)
# ==========================================================
@router.post("/booking/session")
async def create_booking_session(
    check_in: str = Body(...),
    check_out: str = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Create a 15-minute booking session.
    Session expiry is NOW + 15 minutes (frontend can override).
    
    Body:
    {
      "check_in": "2025-12-15",
      "check_out": "2025-12-18"
    }
    """
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")

    if check_in_date >= check_out_date:
        raise HTTPException(status_code=400, detail="check_in must be before check_out")

    # Session expiry = NOW + 15 minutes
    expiry_time = datetime.utcnow() + timedelta(minutes=15)

    return {
        "session_id": f"sess_{current_user.user_id}_{int(datetime.utcnow().timestamp())}",
        "user_id": current_user.user_id,
        "check_in": check_in,
        "check_out": check_out,
        "expiry_time": expiry_time.isoformat() + "Z",
        "remaining_minutes": 15,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "active"
    }


@router.get("/booking/session/{session_id}")
async def get_booking_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Get booking session details - remaining time, lock count, payment status.
    
    Query: /api/v2/rooms/booking/session/sess_123_1701234567
    """
    # Parse session_id to get user_id and creation_time
    parts = session_id.split("_")
    if len(parts) < 3 or parts[0] != "sess":
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    try:
        session_user_id = int(parts[1])
        session_timestamp = int(parts[2])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if session_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access other user's sessions")

    # Get user's active locks
    result = await db.execute(
        select(RoomAvailabilityLocks).where(
            RoomAvailabilityLocks.user_id == current_user.user_id
        )
    )
    locks = result.scalars().all()

    # Calculate remaining time (max 15 minutes from session creation)
    session_created_at = datetime.fromtimestamp(session_timestamp)
    session_expiry = session_created_at + timedelta(minutes=15)
    now = datetime.utcnow()
    remaining_seconds = (session_expiry - now).total_seconds()
    remaining_minutes = max(0, remaining_seconds / 60)
    is_expired = remaining_seconds <= 0

    # Count non-expired locks
    active_locks = [
        lock for lock in locks 
        if datetime.fromisoformat(lock.expires_at.isoformat().replace("Z", "+00:00")) > now
    ]

    return {
        "session_id": session_id,
        "user_id": current_user.user_id,
        "remaining_minutes": round(remaining_minutes, 1),
        "is_expired": is_expired,
        "locked_rooms_count": len(active_locks),
        "total_locks": len(locks),
        "expiry_time": session_expiry.isoformat() + "Z",
        "status": "expired" if is_expired else "active"
    }


# ==========================================================
# 💳 PAYMENT INITIALIZATION & STATUS
# ==========================================================
@router.post("/booking/payment-start")
async def start_payment(
    session_id: str = Body(...),
    lock_ids: list = Body(...),
    final_amount: float = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Initialize payment processing for a booking session.
    Validates session is not expired and all locks belong to user.
    
    Body:
    {
      "session_id": "sess_123_1701234567",
      "lock_ids": [1, 2, 3],
      "final_amount": 15000.50
    }
    """
    if not lock_ids or len(lock_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one lock_id required")

    if len(lock_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 rooms allowed per booking")

    if final_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    # Parse and validate session
    parts = session_id.split("_")
    if len(parts) < 3 or parts[0] != "sess":
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    try:
        session_user_id = int(parts[1])
        session_timestamp = int(parts[2])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if session_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access other user's sessions")

    # Check session not expired
    session_created_at = datetime.fromtimestamp(session_timestamp)
    session_expiry = session_created_at + timedelta(minutes=15)
    if datetime.utcnow() > session_expiry:
        raise HTTPException(status_code=400, detail="Session expired")

    # Verify all locks belong to user
    result = await db.execute(
        select(RoomAvailabilityLocks).where(
            RoomAvailabilityLocks.lock_id.in_(lock_ids)
        )
    )
    locks = result.scalars().all()

    if len(locks) != len(lock_ids):
        raise HTTPException(status_code=404, detail="Some locks not found")

    for lock in locks:
        if lock.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Lock does not belong to user")

    # Generate payment_id
    import uuid
    payment_id = str(uuid.uuid4())

    # Store payment details in memory/cache (or DB if using booking_payments table)
    # For now, return payment_id with status "pending"
    
    return {
        "payment_id": payment_id,
        "session_id": session_id,
        "lock_ids": lock_ids,
        "amount": final_amount,
        "status": "pending",
        "message": "Payment initialized. Please complete within 15 minutes.",
        "expires_at": session_expiry.isoformat() + "Z"
    }


@router.get("/booking/payment-status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Poll payment status. Returns current state: pending, confirmed, failed.
    Frontend should poll this every 2 seconds during payment confirmation.
    
    Query: /api/v2/rooms/booking/payment-status/UUID
    """
    import uuid
    
    # Validate UUID format
    try:
        uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment ID format")

    # In production: Query booking_payments table
    # For MVP: Return pending (frontend simulates payment confirmation)
    
    return {
        "payment_id": payment_id,
        "status": "pending",
        "message": "Payment processing...",
        "user_id": current_user.user_id
    }
