from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlalchemy_schemas.refunds import Refunds, RefundRoomMap
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms


# ==========================================================
# 🔹 CREATE
# ==========================================================

async def insert_refund_record(db: AsyncSession, data: dict) -> Refunds:
    """
    Create new refund record in database.
    
    Inserts a refund record with initial status INITIATED and timestamps. Flushes to
    database but does not commit, allowing parent transaction to control commit timing.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        data (dict): Refund data including booking_id, user_id, type, status, refund_amount, etc.
    
    Returns:
        Refunds: The newly created refund record with refund_id populated.
    """
    refund_record = Refunds(**data)
    db.add(refund_record)
    await db.flush()
    return refund_record


async def insert_refund_room_map(db: AsyncSession, data: dict) -> RefundRoomMap:
    """
    Create refund-to-room mapping record.
    
    Creates a mapping between a refund and a specific room to track per-room refund amounts.
    This enables tracking which rooms were refunded and their individual refund amounts.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        data (dict): Mapping data including refund_id, booking_id, room_id, refund_amount.
    
    Returns:
        RefundRoomMap: The newly created refund room mapping record.
    """
    refund_room_map_record = RefundRoomMap(**data)
    db.add(refund_room_map_record)
    await db.flush()
    return refund_room_map_record


# ==========================================================
# 🔹 READ
# ==========================================================

async def fetch_refund_by_id(db: AsyncSession, refund_id: int) -> Optional[Refunds]:
    """
    Retrieve refund record by ID.
    
    Fetches a single refund record with all associated details including transaction
    method, timestamps, and related room mappings.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        refund_id (int): The ID of the refund to retrieve.
    
    Returns:
        Optional[Refunds]: The refund record if found, None otherwise.
    """
    query_result = await db.execute(select(Refunds).where(Refunds.refund_id == refund_id))
    return query_result.scalars().first()


async def fetch_booking_by_id(db: AsyncSession, booking_id: int) -> Optional[Bookings]:
    """
    Retrieve booking record by ID.
    
    Fetches a single booking record with all details needed for refund calculation
    (check-in, check-out, total price, status, etc.).
    
    Args:
        db (AsyncSession): Database session for executing the query.
        booking_id (int): The ID of the booking to retrieve.
    
    Returns:
        Optional[Bookings]: The booking record if found, None otherwise.
    """
    query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    return query_result.scalars().first()


async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
    """
    Retrieve room record by ID.
    
    Fetches a single room record to access pricing information used for refund amount
    calculation. Room status is also retrieved for updating to AVAILABLE during refund.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        room_id (int): The ID of the room to retrieve.
    
    Returns:
        Optional[Rooms]: The room record if found, None otherwise.
    """
    query_result = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    return query_result.scalars().first()


async def fetch_booking_room_maps(db: AsyncSession, booking_id: int) -> List[BookingRoomMap]:
    """
    Retrieve all room mappings for a booking.
    
    Fetches all BookingRoomMap records associated with a booking to identify which rooms
    were booked and to deactivate them during full cancellation.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        booking_id (int): The ID of the booking.
    
    Returns:
        List[BookingRoomMap]: List of room mappings for the booking (empty list if none found).
    """
    query_result = await db.execute(select(BookingRoomMap).where(BookingRoomMap.booking_id == booking_id))
    return query_result.scalars().all()


async def fetch_refunds_filtered(
    db: AsyncSession,
    refund_id: Optional[int] = None,
    booking_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[Refunds]:
    """
    Retrieve refunds with multiple filter criteria.
    
    Fetches refund records based on any combination of filters. All filters are optional
    and combined with AND logic. Supports filtering by refund properties and date range.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        refund_id (Optional[int]): Filter by specific refund ID.
        booking_id (Optional[int]): Filter by associated booking ID.
        user_id (Optional[int]): Filter by refund owner user ID.
        status (Optional[str]): Filter by refund status (e.g., INITIATED, PROCESSED, COMPLETED).
        type (Optional[str]): Filter by refund type (e.g., CANCELLATION, PARTIAL_CANCEL).
        from_date (Optional[datetime]): Filter refunds initiated on or after this date.
        to_date (Optional[datetime]): Filter refunds initiated on or before this date.
    
    Returns:
        List[Refunds]: List of refund records matching all specified filter criteria.
    """
    stmt = select(Refunds)
    if refund_id is not None:
        stmt = stmt.where(Refunds.refund_id == refund_id)
    if booking_id is not None:
        stmt = stmt.where(Refunds.booking_id == booking_id)
    if user_id is not None:
        stmt = stmt.where(Refunds.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Refunds.status == status)
    if type is not None:
        stmt = stmt.where(Refunds.type == type)
    if from_date is not None:
        stmt = stmt.where(Refunds.initiated_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Refunds.initiated_at <= to_date)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()
