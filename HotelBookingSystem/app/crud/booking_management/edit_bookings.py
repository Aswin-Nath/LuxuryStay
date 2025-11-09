from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import datetime

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingEdits, BookingRoomMap
from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus


# ===================================================
# BOOKINGS CRUD
# ===================================================

async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Optional[Bookings]:
    stmt = select(Bookings).where(Bookings.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def update_booking_flags(db: AsyncSession, booking: Bookings, is_pre_edit: bool, is_post_edit: bool):
    """Mark booking as pre/post edited."""
    if is_pre_edit:
        booking.is_pre_edit_done = True
    if is_post_edit:
        booking.is_post_edit_done = True
    db.add(booking)
    await db.flush()
    return booking


# ===================================================
# BOOKING EDITS CRUD
# ===================================================

async def create_booking_edit(db: AsyncSession, edit_obj: BookingEdits) -> BookingEdits:
    """Insert a new booking edit entry."""
    db.add(edit_obj)
    await db.flush()
    await db.refresh(edit_obj)
    return edit_obj


async def get_booking_edit_by_id(db: AsyncSession, edit_id: int) -> Optional[BookingEdits]:
    """Retrieve a booking edit by ID."""
    stmt = select(BookingEdits).where(BookingEdits.edit_id == edit_id, BookingEdits.is_deleted == False)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def list_booking_edits_for_booking(db: AsyncSession, booking_id: int) -> List[BookingEdits]:
    """Return all edits for a specific booking."""
    stmt = (
        select(BookingEdits)
        .where(BookingEdits.booking_id == booking_id, BookingEdits.is_deleted == False)
        .order_by(BookingEdits.requested_at.desc())
    )
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def update_booking_edit_status(
    db: AsyncSession,
    edit_id: int,
    status_value: str,
    reviewed_by: Optional[int] = None,
    lock_expires_at: Optional[datetime] = None,
):
    """Update the status and metadata of a booking edit."""
    stmt = (
        update(BookingEdits)
        .where(BookingEdits.edit_id == edit_id)
        .values(
            edit_status=status_value,
            reviewed_by=reviewed_by,
            lock_expires_at=lock_expires_at,
            processed_at=datetime.utcnow() if status_value in ["APPROVED", "REJECTED", "PARTIALLY_APPROVED"] else None,
        )
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.flush()


# ===================================================
# BOOKING ROOM MAP CRUD
# ===================================================

async def get_booking_room_maps(db: AsyncSession, booking_id: int) -> List[BookingRoomMap]:
    stmt = select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def delete_booking_room_map(db: AsyncSession, booking_id: int, room_id: int):
    """Delete a single room mapping for a booking."""
    stmt = delete(BookingRoomMap).where(
        BookingRoomMap.booking_id == booking_id, BookingRoomMap.room_id == room_id
    )
    await db.execute(stmt)
    await db.flush()


async def insert_booking_room_map(db: AsyncSession, room_map_obj: BookingRoomMap):
    """Insert new booking-room mapping (for room replacements)."""
    db.add(room_map_obj)
    await db.flush()
    return room_map_obj


# ===================================================
# REFUNDS CRUD
# ===================================================

async def create_refund(db: AsyncSession, refund_obj: Refunds) -> Refunds:
    db.add(refund_obj)
    await db.flush()
    return refund_obj


async def create_refund_room_map(db: AsyncSession, refund_room_map_obj: RefundRoomMap):
    db.add(refund_room_map_obj)
    await db.flush()
    return refund_room_map_obj


# ===================================================
# ROOMS CRUD (for lock/unlock actions)
# ===================================================

async def get_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
    stmt = select(Rooms).where(Rooms.room_id == room_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def lock_room(db: AsyncSession, room_id: int):
    """Set room to FROZEN (ADMIN_LOCK)."""
    room = await get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.room_status != RoomStatus.AVAILABLE:
        return {"message": "Room not available for lock"}
    room.room_status = RoomStatus.FROZEN
    room.freeze_reason = "ADMIN_LOCK"
    db.add(room)
    await db.flush()
    return room


async def unlock_room(db: AsyncSession, room_id: int):
    """Set room to AVAILABLE (NONE)."""
    room = await get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.room_status = RoomStatus.AVAILABLE
    room.freeze_reason = "NONE"
    db.add(room)
    await db.flush()
    return room
