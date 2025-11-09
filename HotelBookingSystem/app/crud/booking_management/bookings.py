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
    """Insert a new booking record."""
    db.add(booking_obj)
    await db.flush()
    return booking_obj


async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Bookings:
    """Fetch a single booking with its related rooms and taxes."""
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
    """List all bookings with pagination."""
    stmt = (
        select(Bookings)
        .options(joinedload(Bookings.rooms), joinedload(Bookings.taxes))
        .limit(limit)
        .offset(offset)
    )
    query_result = await db.execute(stmt)
    return query_result.unique().scalars().all()


async def update_booking_status(db: AsyncSession, booking_id: int, status: str) -> None:
    """Update booking status."""
    stmt = (
        update(Bookings)
        .where(Bookings.booking_id == booking_id)
        .values(status=status)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()


async def delete_booking(db: AsyncSession, booking_id: int) -> None:
    """Soft delete a booking or perform hard delete."""
    stmt = delete(Bookings).where(Bookings.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# BOOKING ROOM MAP CRUD
# ==============================

async def create_booking_room_map(db: AsyncSession, brm_obj: BookingRoomMap) -> BookingRoomMap:
    """Insert a record into booking_room_map."""
    db.add(brm_obj)
    await db.flush()
    return brm_obj


async def get_rooms_for_booking(db: AsyncSession, booking_id: int) -> List[BookingRoomMap]:
    """Retrieve room mappings for a booking."""
    stmt = select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def delete_booking_room_maps(db: AsyncSession, booking_id: int) -> None:
    """Delete all room mappings for a booking."""
    stmt = delete(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# BOOKING TAX MAP CRUD
# ==============================

async def create_booking_tax_map(db: AsyncSession, tax_map_obj: BookingTaxMap) -> BookingTaxMap:
    """Insert a record into booking_tax_map."""
    db.add(tax_map_obj)
    await db.flush()
    return tax_map_obj


async def get_tax_for_booking(db: AsyncSession, booking_id: int) -> Optional[BookingTaxMap]:
    """Retrieve tax mapping for a booking."""
    stmt = select(BookingTaxMap).where(BookingTaxMap.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def delete_booking_tax_map(db: AsyncSession, booking_id: int) -> None:
    """Delete the tax map entry for a booking."""
    stmt = delete(BookingTaxMap).where(BookingTaxMap.booking_id == booking_id)
    await db.execute(stmt)
    await db.commit()


# ==============================
# PAYMENTS CRUD
# ==============================

async def create_payment(db: AsyncSession, payment_obj: PaymentsModel) -> PaymentsModel:
    """Insert a payment record."""
    db.add(payment_obj)
    await db.flush()
    return payment_obj


async def get_payment_by_booking(db: AsyncSession, booking_id: int) -> Optional[PaymentsModel]:
    """Retrieve payment record linked to a booking."""
    stmt = select(PaymentsModel).where(PaymentsModel.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def delete_payment(db: AsyncSession, payment_id: int) -> None:
    """Delete a payment record."""
    stmt = delete(PaymentsModel).where(PaymentsModel.payment_id == payment_id)
    await db.execute(stmt)
    await db.commit()
