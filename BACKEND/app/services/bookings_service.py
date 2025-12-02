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


async def query_bookings(
    db: AsyncSession, 
    user_id: Optional[int] = None, 
    status: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    room_type_id: Optional[int] = None,
    check_in_date: Optional[date] = None,
    check_out_date: Optional[date] = None,
    limit: int = 20, offset: int = 0
):
    """
    Query bookings with advanced filtering options.
    
    Retrieves bookings filtered by multiple criteria including user ID, booking status, price range,
    room types, and check-in/check-out dates. Eagerly loads related rooms and taxes.
    
    Args:
        db (AsyncSession): The database session for executing queries.
        user_id (Optional[int]): Filter by user ID. If None, no user filtering applied.
        status (Optional[str]): Filter by booking status (e.g., 'CONFIRMED', 'CANCELLED', 'COMPLETED').
        min_price (Optional[Decimal]): Filter bookings with total_price >= min_price.
        max_price (Optional[Decimal]): Filter bookings with total_price <= max_price.
        room_types (Optional[List[int]]): Filter by room type IDs. Booking must have rooms of specified types.
        check_in_date (Optional[date]): Filter bookings with check_in >= this date.
        check_out_date (Optional[date]): Filter bookings with check_out <= this date.
    
    Returns:
        List[Bookings]: A list of booking records matching all filter criteria, with rooms and taxes loaded.
    
    Examples:
        # Get all bookings for user with price between 100-500
        await query_bookings(db, user_id=5, min_price=100, max_price=500)
        
        # Get upcoming bookings in January for luxury rooms
        await query_bookings(db, check_in_date=date(2025,1,1), room_types=[2, 3])
    """
    stmt = select(Bookings).options(joinedload(Bookings.rooms), joinedload(Bookings.taxes)).limit(limit).offset(offset)
    
    # Apply filters
    if user_id:
        stmt = stmt.where(Bookings.user_id == user_id)
    
    if status:
        stmt = stmt.where(Bookings.status == status)
    
    if min_price is not None:
        stmt = stmt.where(Bookings.total_price >= min_price)
    
    if max_price is not None:
        stmt = stmt.where(Bookings.total_price <= max_price)
    
    if check_in_date:
        stmt = stmt.where(Bookings.check_in >= check_in_date)
    
    if check_out_date:
        stmt = stmt.where(Bookings.check_out <= check_out_date)
    
    # Room type filtering - join with BookingRoomMap and RoomTypes
    if room_type_id:
        stmt = stmt.where(
            exists(
                select(BookingRoomMap).where(
                    and_(
                        BookingRoomMap.booking_id == Bookings.booking_id,
                        BookingRoomMap.room_type_id==room_type_id
                    )
                )
            )
        )

    query_result = await db.execute(stmt)
    return query_result.unique().scalars().all()
