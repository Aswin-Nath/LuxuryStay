"""
Background worker for releasing expired room holds.

This worker runs periodically (every minute recommended) to:
1. Find all rooms with HELD status
2. Check if hold_expires_at < current_time
3. Release expired holds back to AVAILABLE status
4. Clear hold_expires_at timestamp

This ensures rooms are automatically released after the booking hold expires,
allowing other customers to book them.
"""

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio
import logging

from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus
from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.database.postgres_connection import DATABASE_URL

# Setup logging
logger = logging.getLogger(__name__)

# ========== DATABASE CONNECTION SETUP ==========
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def release_expired_room_holds():
    """
    Release all rooms with expired holds back to AVAILABLE status.
    Mark associated bookings status as EXPIRED.
    
    Queries for all rooms with:
    - room_status = HELD
    - hold_expires_at < current_utc_time
    
    Updates them to:
    - room_status = AVAILABLE
    - hold_expires_at = NULL
    
    Also marks all bookings that have these rooms as:
    - status = EXPIRED
    
    This allows other customers to book these rooms and prevents payments on expired bookings.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get current UTC time
            now_utc = datetime.utcnow()
            
            # ========== FIND ALL EXPIRED HOLDS ==========
            query = await db.execute(
                select(Rooms).where(
                    Rooms.room_status == RoomStatus.HELD,
                    Rooms.hold_expires_at < now_utc
                )
            )
            expired_rooms = query.scalars().all()
            
            if not expired_rooms:
                logger.info("[ROOM HOLDS] No expired holds to release")
                return
            
            # ========== COLLECT BOOKING IDs ASSOCIATED WITH EXPIRED ROOMS ==========
            expired_room_ids = [room.room_id for room in expired_rooms]
            
            # Find all booking IDs that have these expired rooms
            booking_query = await db.execute(
                select(BookingRoomMap.booking_id).where(
                    BookingRoomMap.room_id.in_(expired_room_ids)
                )
            )
            affected_booking_ids = set(booking_query.scalars().all())
            
            # ========== RELEASE EXPIRED HOLDS & MARK BOOKINGS AS EXPIRED ==========
            released_count = 0
            for room in expired_rooms:
                logger.info(
                    f"[ROOM HOLDS] Releasing hold for room_id={room.room_id} "
                    f"(expired at {room.hold_expires_at})"
                )
                room.room_status = 'AVAILABLE'
                room.hold_expires_at = None
                released_count += 1
            
            # Mark all affected bookings as EXPIRED by updating their status
            if affected_booking_ids:
                expire_bookings_stmt = (
                    update(Bookings)
                    .where(Bookings.booking_id.in_(affected_booking_ids))
                    .values(status="EXPIRED")
                )
                await db.execute(expire_bookings_stmt)
                logger.info(
                    f"[ROOM HOLDS] Marked {len(affected_booking_ids)} booking(s) as EXPIRED: {affected_booking_ids}"
                )
            
            # ========== COMMIT CHANGES ==========
            await db.commit()
            
            logger.info(
                f"[ROOM HOLDS] Successfully released {released_count} expired room hold(s) "
                f"and marked {len(affected_booking_ids)} booking(s) as expired"
            )
            
        except Exception as e:
            logger.error(f"[ROOM HOLDS] Error releasing expired holds: {str(e)}")
            await db.rollback()
            raise


async def run_hold_release_scheduler(interval_seconds: int = 60):
    """
    Run the hold release task on a schedule.
    
    Args:
        interval_seconds (int): How often to check for expired holds (default: 60 seconds)
    
    This should be started as a background task when the application starts.
    """
    logger.info(f"[ROOM HOLDS] Scheduler started with {interval_seconds}s interval")
    
    while True:
        try:
            await release_expired_room_holds()
        except Exception as e:
            logger.error(f"[ROOM HOLDS] Scheduler error: {str(e)}")
        
        # Wait before next check
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    """
    Run directly for testing purposes.
    In production, this should be integrated with your application startup.
    """
    asyncio.run(run_hold_release_scheduler())
