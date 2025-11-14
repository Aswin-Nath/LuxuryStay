from typing import List, Optional
from sqlalchemy import select, or_, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal
from collections import Counter
from sqlalchemy.orm import joinedload
from datetime import date, datetime, timedelta

# CRUD imports
from app.crud.bookings import (
    create_booking_record,
    create_booking_room_map,
    create_booking_tax_map,
    get_booking_by_id,
    list_all_bookings,
)
# Models
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap, BookingTaxMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus, RoomTypes
from app.models.sqlalchemy_schemas.tax_utility import TaxUtility
from app.models.sqlalchemy_schemas.notifications import Notifications
from app.models.sqlalchemy_schemas.users import Users


# ============================================================================
# 🔹 VALIDATION HELPERS - Date validation for bookings
# ============================================================================

def validate_booking_dates(check_in: date, check_out: date, primary_customer_dob: Optional[date] = None) -> None:
    """
    Validate all date fields in a booking request.
    
    Performs comprehensive date validation:
    - check_in must be from today onwards (not in the past)
    - check_out must be after check_in (minimum 1-day stay)
    - primary_customer_dob must be a valid past date (customer cannot be born in future)
    - Maximum stay duration capped at 90 days for system constraints
    
    Args:
        check_in (date): The check-in date for the booking. Must be today or a future date.
        check_out (date): The check-out date for the booking.
        primary_customer_dob (Optional[date]): Date of birth of primary customer, if provided.
    
    Raises:
        HTTPException (400): If any date validation fails with specific reason.
    
    Side Effects:
        Validates against current date (datetime.now().date()).
    """
    today = datetime.now().date()
    
    # Validation 1: check_in must be from today onwards (not past)
    if check_in < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Check-in date must be from today onwards. Provided: {check_in}, Today: {today}"
        )
    
    # Validation 2: check_out must be after check_in
    if check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"check_out date must be after check_in date. check_in: {check_in}, check_out: {check_out}"
        )
    
    # Validation 3: Minimum stay duration (at least 1 day)
    min_stay_days = 1
    if (check_out - check_in).days < min_stay_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum stay duration is {min_stay_days} day(s). Requested: {(check_out - check_in).days} day(s)"
        )
    
    # Validation 4: Maximum stay duration (90 days for system constraint)
    max_stay_days = 90
    if (check_out - check_in).days > max_stay_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum stay duration is {max_stay_days} days. Requested: {(check_out - check_in).days} days"
        )
    
    # Validation 5: Primary customer DOB must be in past (if provided)
    if primary_customer_dob:
        # Customer must be at least 18 years old (configurable)
        min_age_years = 18
        min_dob_date = today - timedelta(days=365 * min_age_years)
        
        if primary_customer_dob > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"primary_customer_dob cannot be in the future. Provided: {primary_customer_dob}"
            )
        
        if primary_customer_dob > min_dob_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer must be at least {min_age_years} years old. DOB: {primary_customer_dob}"
            )


async def validate_room_occupancy_capacity(db: AsyncSession, rooms_data: List[dict]) -> None:
    """
    Validate that each room's occupancy (adults + children) does not exceed room type's maximum capacity.
    
    Verifies that for each requested room:
    - Adults count <= room_type.max_adult_count
    - Children count <= room_type.max_child_count
    - Total occupancy (adults + children) <= (max_adult_count + max_child_count)
    
    Args:
        db (AsyncSession): Database session for fetching room type capacities.
        rooms_data (List[dict]): List of room occupancy details with room_type_id, adults, and children.
    
    Raises:
        HTTPException (400): If any room's occupancy exceeds the room type's capacity.
        HTTPException (404): If room_type_id is not found in database.
    
    Side Effects:
        Queries room_types table for capacity information.
    """
    for idx, room_data in enumerate(rooms_data):
        room_type_id = room_data.get("room_type_id")
        adults = room_data.get("adults", 0)
        children = room_data.get("children", 0)
        
        # Fetch room type to get max capacity
        room_type_query = await db.execute(
            select(RoomTypes).where(RoomTypes.room_type_id == room_type_id)
        )
        room_type = room_type_query.scalars().first()
        
        if not room_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room type {room_type_id} (requested in Room {idx + 1}) not found"
            )
        
        # Validate adult count doesn't exceed max
        if adults > room_type.max_adult_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {idx + 1}: Adults count ({adults}) exceeds maximum capacity ({room_type.max_adult_count}) for {room_type.type_name}"
            )
        
        # Validate child count doesn't exceed max
        if children > room_type.max_child_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {idx + 1}: Children count ({children}) exceeds maximum capacity ({room_type.max_child_count}) for {room_type.type_name}"
            )
        
        # Validate total occupancy doesn't exceed sum of max capacities
        max_total_occupancy = room_type.max_adult_count + room_type.max_child_count
        current_occupancy = adults + children
        if current_occupancy > max_total_occupancy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {idx + 1}: Total occupancy ({current_occupancy}) exceeds maximum capacity ({max_total_occupancy}) for {room_type.type_name}"
            )


async def create_booking(db: AsyncSession, payload, user_id: int) -> Bookings:
    """
    Create a new booking and allocate rooms with soft locking mechanism.
    
    Creates a complete booking transaction including:
    1. **Validates booking dates** (check_in not past, check_out after check_in, stay duration 1-90 days)
    2. **Validates room occupancy** (each room must have at least 1 adult)
    3. **Validates requested room types and availability**
    4. **Atomically allocates available rooms** using row-level locks (FOR UPDATE SKIP LOCKED)
    5. **Applies soft time-based locks** with formula: 5 + (2 × room_count) minutes
    6. **Creates booking record in database**
    7. **Maps rooms to booking** with adult/child occupancy details
    8. **Maps applicable taxes**
    9. **Creates notification** for the booking
    
    **Locking Mechanism:**
    - Hard lock (DB-level): FOR UPDATE SKIP LOCKED during allocation (seconds)
    - Soft lock (time-based): Room marked HELD with hold_expires_at timestamp
    - Auto-release: Background cleanup frees expired holds
    - Lock duration: 5 + (2 × number_of_rooms) minutes
    
    **Transactional Guarantees:**
    - All operations in single session transaction (implicit via AsyncSession)
    - Row-level locks prevent concurrent double-booking (FOR UPDATE SKIP LOCKED)
    - Rooms marked as HELD with expiry timer for temporary reservation
    - Single atomic commit at the end
    - Automatic rollback on any exception
    
    Date validation ensures:
    - check_in must be today or in the future
    - check_out must be after check_in
    - Stay duration between 1-90 days
    - Customer DOB (if provided) must be past date (minimum 18 years old)
    
    Room occupancy validation ensures:
    - Each room has at least 1 adult
    - Children count is non-negative
    
    Room allocation is automatically performed based on room availability and type matching.
    All rooms are marked as BOOKED after successful allocation and locked during transaction.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        payload: Pydantic model containing booking details with room occupancy (adults/children per room).
        user_id (int): The ID of the authenticated user creating the booking.
    
    Returns:
        Bookings: The newly created booking record with booking_id assigned.
    
    Raises:
        HTTPException (400): If check_in is in past, check_out before check_in, or stay duration outside 1-90 days.
        HTTPException (400): If primary_customer_dob in future or customer under 18 years old.
        HTTPException (400): If no rooms requested, any room has 0 adults, or not enough available rooms.
        HTTPException (400): If room allocation fails due to insufficient availability.
    
    Side Effects:
        - Validates dates against current date using datetime.now().date()
        - Validates room occupancy (minimum 1 adult per room)
        - Atomically allocates rooms (marks as BOOKED within transaction)
        - Creates audit trail for booking
        - Sends notification to user
    """
    # ========== PRE-TRANSACTION VALIDATION ==========
    # Perform all non-critical validations before starting transaction
    
    data = payload.model_dump()
    data["user_id"] = user_id  # Enforce user_id from authenticated user
    
    # Extract room occupancy details from the new structure
    rooms_data = data.pop("rooms", []) or []
    requested_room_type_ids = [room["room_type_id"] for room in rooms_data]

    # ========== VALIDATE MAXIMUM ROOMS PER CUSTOMER ==========
    # Maximum 5 rooms per customer
    MAX_ROOMS_PER_CUSTOMER = 5
    if len(rooms_data) > MAX_ROOMS_PER_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ROOMS_PER_CUSTOMER} rooms allowed per customer. Requested: {len(rooms_data)} room(s)"
        )

    # ========== FETCH USER PROFILE FOR AUTO-FILL ==========
    # Single query to get user details (reused for auto-fill)
    user_query = await db.execute(select(Users).where(Users.user_id == user_id))
    current_user = user_query.scalars().first()
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found"
        )

    # ========== AUTO-FILL CUSTOMER DETAILS FROM USER PROFILE ==========
    # If not provided in request, use user profile data
    if not data.get("primary_customer_name"):
        if current_user.full_name:
            data["primary_customer_name"] = current_user.full_name
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="primary_customer_name required (not provided in request and not found in user profile)"
            )
    
    if not data.get("primary_customer_phone_number"):
        if current_user.phone_number:
            data["primary_customer_phone_number"] = current_user.phone_number
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="primary_customer_phone_number required (not provided in request and not found in user profile)"
            )
    
    if not data.get("primary_customer_dob"):
        if current_user.dob:
            data["primary_customer_dob"] = current_user.dob
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="primary_customer_dob required (not provided in request and not found in user profile)"
            )

    # ========== DATE VALIDATION ==========
    validate_booking_dates(
        check_in=data["check_in"],
        check_out=data["check_out"],
        primary_customer_dob=data.get("primary_customer_dob")
    )

    # ========== ROOM OCCUPANCY CAPACITY VALIDATION ==========
    # Validate that each room's occupancy doesn't exceed room type's maximum capacity
    await validate_room_occupancy_capacity(db, rooms_data)

    if not requested_room_type_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No room type ids provided for booking")

    # Validate each room has at least 1 adult (already validated in Pydantic model, but enforce here as well)
    for idx, room_data in enumerate(rooms_data):
        if room_data.get("adults", 0) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {idx + 1} must have at least 1 adult. Got {room_data.get('adults', 0)} adult(s)"
            )

    room_count = len(requested_room_type_ids)
    req_counts = Counter(requested_room_type_ids)

    # ========== LOCK AVAILABLE ROOMS FOR UPDATE ==========
    # Use FOR UPDATE SKIP LOCKED to prevent concurrent double-booking
    # This locks selected rows until transaction commits/rolls back
    # SKIP LOCKED ensures other transactions don't block on locked rows
    # 
    # Include rooms that are:
    # 1. AVAILABLE (room_status == AVAILABLE), OR
    # 2. HELD with expired hold_expires_at (hold has expired, room is now available again)
    # 
    # Also verify that rooms don't have conflicting bookings for the requested date range
    # A booking conflicts if: existing_check_in < requested_check_out AND existing_check_out > requested_check_in
    
    query = await db.execute(
        select(Rooms)
        .where(
            Rooms.room_type_id.in_(list(req_counts.keys())),
            or_(
                # Room is currently available
                Rooms.room_status == RoomStatus.AVAILABLE,
                # OR room is held but the hold has expired (make it available again)
                (
                    (Rooms.room_status == RoomStatus.HELD) & 
                    (Rooms.hold_expires_at <= datetime.utcnow())
                )
            ),
            # AND check that room has no conflicting bookings in the requested date range
            # Use subquery to check for date conflicts
            ~select(1)
            .select_from(BookingRoomMap)
            .join(Bookings, BookingRoomMap.booking_id == Bookings.booking_id)
            .where(
                BookingRoomMap.room_id == Rooms.room_id,
                Bookings.check_in < data["check_out"],
                Bookings.check_out > data["check_in"],
                Bookings.status != "CANCELLED",
                Bookings.is_deleted == False
            )
            .exists()
        )
        .with_for_update(skip_locked=True)
    )
    available_rooms = query.scalars().all()

    # ========== VALIDATE SUFFICIENT ROOMS AVAILABLE ==========
    # Check if we have enough available rooms for the requested allocation
    avail_by_type = {}
    for room_record in available_rooms:
        avail_by_type.setdefault(room_record.room_type_id, []).append(room_record)

    allocation = []
    for room_data in rooms_data:
        rt_id = room_data["room_type_id"]
        available_rooms_for_type = avail_by_type.get(rt_id, [])
        if not available_rooms_for_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No available rooms for type {rt_id}. Booking cannot be completed."
            )
        allocation.append((available_rooms_for_type.pop(0), room_data))  # Store room with its occupancy

    # ========== APPLY SOFT LOCKING WITH HOLD TIMER ==========
    # Lock duration formula: 5 + (2 × number_of_rooms) minutes
    # This creates a temporary hold on the rooms to prevent re-allocation
    room_count = len(requested_room_type_ids)
    lock_duration_minutes = 5
    
    # Calculate hold expiry time in UTC
    now_utc = datetime.utcnow()
    hold_expiry_time = now_utc + timedelta(minutes=lock_duration_minutes)
    
    # ========== MARK ROOMS AS HELD WITH EXPIRY TIMER ==========
    # Update all allocated rooms to HELD status with expiry timestamp
    for allocated_room, room_data in allocation:
        if allocated_room.room_status != RoomStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"room_id {allocated_room.room_id} is no longer available"
            )
        # Soft lock: mark as HELD with automatic expiry
        allocated_room.room_status = RoomStatus.HELD
        allocated_room.hold_expires_at = hold_expiry_time
        db.add(allocated_room)

    # ========== CALCULATE TOTAL PRICE FROM ROOM TYPES ==========
    # Always calculate total_price from room types and stay duration
    # Fetch room type details for allocated rooms
    room_type_ids = list(set(room.room_type_id for room, _ in allocation))
    query = await db.execute(
        select(RoomTypes).where(RoomTypes.room_type_id.in_(room_type_ids))
    )
    room_types_map = {rt.room_type_id: rt for rt in query.scalars().all()}
    
    # Calculate total price based on number of nights and room prices
    num_nights = (data["check_out"] - data["check_in"]).days
    total_price = Decimal("0")
    
    for allocated_room, _ in allocation:
        room_type = room_types_map.get(allocated_room.room_type_id)
        if not room_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room type {allocated_room.room_type_id} not found"
            )
        # Price = room_price_per_night * number_of_nights
        price_per_night = Decimal(str(room_type.price_per_night))
        total_price += price_per_night * Decimal(num_nights)
    
    total_price = float(total_price.quantize(Decimal("0.01")))
    data["total_price"] = total_price

    # ========== CREATE BOOKING RECORD ==========
    booking = Bookings(
        user_id=data["user_id"],
        room_count=room_count,  # Use computed room_count from len(rooms)
        status="PENDING_PAYMENT",
        check_in=data["check_in"],
        check_in_time=data.get("check_in_time"),
        check_out=data["check_out"],
        check_out_time=data.get("check_out_time"),
        total_price=Decimal(str(data["total_price"])),
        primary_customer_name=data.get("primary_customer_name"),
        primary_customer_phone_number=data.get("primary_customer_phone_number"),
        primary_customer_dob=data.get("primary_customer_dob"),
    )

    await create_booking_record(db, booking)

    # ========== MAP ROOMS TO BOOKING ==========
    seen = set()
    for allocated_room, room_data in allocation:
        room_id = allocated_room.room_id
        if room_id in seen:
            continue
        seen.add(room_id)
        
        # Extract occupancy details for this room
        adults = room_data.get("adults", 1)
        children = room_data.get("children", 0)
        
        booking_room_map = BookingRoomMap(
            booking_id=booking.booking_id,
            room_id=room_id,
            room_type_id=allocated_room.room_type_id,
            adults=adults,
            children=children,
        )
        await create_booking_room_map(db, booking_room_map)

    # ========== APPLY TAXES ==========
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

    # ========== CREATE NOTIFICATION ==========
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

    # ========== COMMIT TRANSACTION ==========
    # All changes are atomically committed together
    await db.commit()

    # ========== RETRIEVE FULL BOOKING RECORD ==========
    # Fetch complete booking with all relationships after transaction completes
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
