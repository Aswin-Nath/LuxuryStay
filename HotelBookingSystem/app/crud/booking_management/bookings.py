from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap, BookingTaxMap
from app.models.sqlalchemy_schemas.payments import Payments as PaymentsModel


# ==============================
# BOOKINGS CRUD
# ==============================

async def create_booking_record(db: AsyncSession, booking_obj: Bookings) -> Bookings:
    """
    Insert a new booking record into the database.
    
    Adds a booking object to the session and flushes (does not commit).
    The caller is responsible for commit.
    
    Args:
        db (AsyncSession): The async database session.
        booking_obj (Bookings): The booking object to insert.
    
    Returns:
        Bookings: The booking object (flushed but not yet committed).
    """
    db.add(booking_obj)
    await db.flush()
    return booking_obj


async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Bookings:
    """
    Fetch a single booking with its related rooms and taxes.
    
    Retrieves a booking by ID and eagerly loads related rooms and taxes data.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The unique identifier of the booking.
    
    Returns:
        Bookings: The booking record with rooms and taxes loaded.
    
    Raises:
        HTTPException (404): If booking with the specified ID is not found.
    """
    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .where(Bookings.booking_id == booking_id)
    )
    query_result = await db.execute(stmt)
    booking = query_result.scalars().first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


async def list_all_bookings(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Bookings]:
    """
    List all bookings with pagination and related data.
    
    Retrieves multiple bookings with offset and limit for pagination.
    Eagerly loads related rooms and taxes for each booking.
    
    Args:
        db (AsyncSession): The async database session.
        limit (int): Maximum number of bookings to return (default: 20).
        offset (int): Number of bookings to skip from the start (default: 0).
    
    Returns:
        List[Bookings]: A list of booking records with related data loaded.
    """
    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .limit(limit)
        .offset(offset)
    )
    query_result = await db.execute(stmt)
    return query_result.unique().scalars().all()


async def update_booking_status(db: AsyncSession, booking_id: int, status: str) -> None:
    """
    Update a booking's status.
    
    Updates the status field of a booking record in the database.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking to update.
        status (str): The new booking status (e.g., 'CONFIRMED', 'CANCELLED', 'COMPLETED').
    
    Returns:
        None
    """
    stmt = (
        update(Bookings)
        .where(Bookings.booking_id == booking_id)
        .values(status=status)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()


async def delete_booking(db: AsyncSession, booking_id: int) -> None:
    """
    Delete a booking record from the database.
    
    Removes a booking record permanently from the database.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking to delete.
    
    Returns:
        None
    """
    stmt = delete(Bookings).where(Bookings.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# BOOKING ROOM MAP CRUD
# ==============================

async def create_booking_room_map(db: AsyncSession, brm_obj: BookingRoomMap) -> BookingRoomMap:
    """
    Insert a booking-room mapping record.
    
    Links a room to a booking, recording occupancy details (adults, children, etc).
    
    Args:
        db (AsyncSession): The async database session.
        brm_obj (BookingRoomMap): The booking-room mapping object.
    
    Returns:
        BookingRoomMap: The mapping object (flushed but not yet committed).
    """
    db.add(brm_obj)
    await db.flush()
    return brm_obj


async def get_rooms_for_booking(db: AsyncSession, booking_id: int) -> List[BookingRoomMap]:
    """
    Retrieve all room mappings for a booking.
    
    Fetches all rooms allocated to a specific booking with their occupancy details.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking.
    
    Returns:
        List[BookingRoomMap]: List of room mappings for the booking.
    """
    stmt = select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def delete_booking_room_maps(db: AsyncSession, booking_id: int) -> None:
    """
    Delete all room mappings for a booking.
    
    Removes all room-to-booking associations when a booking is cancelled or deleted.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking whose room mappings to delete.
    
    Returns:
        None
    """
    stmt = delete(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# BOOKING TAX MAP CRUD
# ==============================

async def create_booking_tax_map(db: AsyncSession, tax_map_obj: BookingTaxMap) -> BookingTaxMap:
    """
    Insert a booking-tax mapping record.
    
    Links applicable taxes to a booking for tracking tax obligations and calculations.
    
    Args:
        db (AsyncSession): The async database session.
        tax_map_obj (BookingTaxMap): The booking-tax mapping object.
    
    Returns:
        BookingTaxMap: The mapping object (flushed but not yet committed).
    """
    db.add(tax_map_obj)
    await db.flush()
    return tax_map_obj


async def get_tax_for_booking(db: AsyncSession, booking_id: int) -> Optional[BookingTaxMap]:
    """
    Retrieve tax mapping for a booking.
    
    Fetches tax details associated with a specific booking.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking.
    
    Returns:
        Optional[BookingTaxMap]: The tax mapping if found, None otherwise.
    """
    stmt = select(BookingTaxMap).where(BookingTaxMap.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def delete_booking_tax_map(db: AsyncSession, booking_id: int) -> None:
    """
    Delete the tax map entry for a booking.
    
    Removes tax-to-booking association when a booking is cancelled or modified.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking.
    
    Returns:
        None
    """
    stmt = delete(BookingTaxMap).where(BookingTaxMap.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# PAYMENTS CRUD
# ==============================

async def create_payment(db: AsyncSession, payment_obj: PaymentsModel) -> PaymentsModel:
    """
    Insert a payment record.
    
    Records a payment made for a booking (full or partial payment).
    
    Args:
        db (AsyncSession): The async database session.
        payment_obj (PaymentsModel): The payment object to insert.
    
    Returns:
        PaymentsModel: The payment object (flushed but not yet committed).
    """
    db.add(payment_obj)
    await db.flush()
    return payment_obj


async def get_payment_by_booking(db: AsyncSession, booking_id: int) -> Optional[PaymentsModel]:
    """
    Retrieve payment record linked to a booking.
    
    Fetches the payment details for a specific booking.
    
    Args:
        db (AsyncSession): The async database session.
        booking_id (int): The ID of the booking.
    
    Returns:
        Optional[PaymentsModel]: The payment record if found, None otherwise.
    """
    stmt = select(PaymentsModel).where(PaymentsModel.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def delete_payment(db: AsyncSession, payment_id: int) -> None:
    """
    Delete a payment record.
    
    Removes a payment record from the database (used when refunding or correcting payments).
    
    Args:
        db (AsyncSession): The async database session.
        payment_id (int): The ID of the payment to delete.
    
    Returns:
        None
    """
    stmt = delete(PaymentsModel).where(PaymentsModel.payment_id == payment_id)
    await db.execute(stmt)
    await db.commit()
