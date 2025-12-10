"""
Hourly worker for updating booking and room lifecycle.

This worker runs every hour to:
1. Find all bookings with status 'Confirmed' where check_in date is today
2. Update booking status from 'Confirmed' to 'Checked-In'
3. Update room status of all rooms in that booking from 'AVAILABLE' to 'currently occupied'

This ensures that when a guest's check-in date arrives, their booking and rooms are automatically
marked as checked-in and occupied.
"""

from datetime import date
from sqlalchemy import select
import asyncio
import logging

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import RoomStatus
from app.database.postgres_connection import AsyncSessionLocal
# Setup logging
logger = logging.getLogger(__name__)



async def update_bookings_to_checked_in():
    """
    Check for bookings with status 'Confirmed' where check_in date is today.
    Update their status to 'Checked-In' and mark associated rooms as 'BOOKED' (currently occupied).
    
    Process:
    1. Get today's date
    2. Find all bookings where:
       - status = 'Confirmed'
       - check_in = today's date
       - is_deleted = false
    3. For each booking:
       - Update booking.status = 'Checked-In'
       - Get all rooms in that booking via BookingRoomMap
       - Update each room's room_status = 'BOOKED'
    4. Commit changes
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get today's date (without time)
            today = date.today()
            
            # ========== FIND ALL CONFIRMED BOOKINGS WITH TODAY AS CHECK-IN ==========
            query = await db.execute(
                select(Bookings).where(
                    Bookings.status == "Confirmed",
                    Bookings.check_in == today,
                    Bookings.is_deleted.is_(False)
                )
            )
            bookings_to_check_in = query.scalars().all()
            
            if not bookings_to_check_in:
                logger.info("[BOOKING LIFECYCLE] No confirmed bookings with check-in today")
                return
            
            logger.info(
                f"[BOOKING LIFECYCLE] Found {len(bookings_to_check_in)} booking(s) to check in"
            )
            
            # ========== UPDATE BOOKINGS AND ASSOCIATED ROOMS ==========
            checked_in_count = 0
            rooms_occupied_count = 0
            
            for booking in bookings_to_check_in:
                try:
                    # Update booking status to Checked-In
                    booking.status = "Checked-In"
                    checked_in_count += 1
                    
                    logger.info(
                        f"[BOOKING LIFECYCLE] Booking {booking.booking_id}: "
                        f"status updated to 'Checked-In'"
                    )
                    
                    # ========== FETCH AND UPDATE ROOMS ==========
                    # Get all rooms for this booking
                    room_map_query = await db.execute(
                        select(BookingRoomMap).where(
                            BookingRoomMap.booking_id == booking.booking_id
                        )
                    )
                    room_maps = room_map_query.scalars().all()
                    
                    for room_map in room_maps:
                        # Update room status to BOOKED (currently occupied)
                        room = room_map.room
                        if room:
                            room.room_status = RoomStatus.BOOKED
                            rooms_occupied_count += 1
                            
                            logger.info(
                                f"[BOOKING LIFECYCLE] Room {room.room_id} (Room No: {room.room_no}): "
                                f"status updated to 'BOOKED' (occupied)"
                            )
                
                except Exception as e:
                    logger.error(
                        f"[BOOKING LIFECYCLE] Error processing booking {booking.booking_id}: {str(e)}"
                    )
                    await db.rollback()
                    raise
            
            # ========== COMMIT CHANGES ==========
            await db.commit()
            
            logger.info(
                f"[BOOKING LIFECYCLE] Successfully updated {checked_in_count} booking(s) to 'Checked-In' "
                f"and marked {rooms_occupied_count} room(s) as 'BOOKED'"
            )
            
        except Exception as e:
            logger.error(f"[BOOKING LIFECYCLE] Error in hourly check-in update: {str(e)}")
            await db.rollback()
            raise


async def run_hourly_booking_lifecycle_scheduler(interval_seconds: int = 3600):
    """
    Run the booking lifecycle update task hourly.
    
    Args:
        interval_seconds (int): How often to check for bookings to check in (default: 3600 seconds = 1 hour)
    
    This should be started as a background task when the application starts.
    """
    logger.info(f"[BOOKING LIFECYCLE] Hourly scheduler started with {interval_seconds}s interval")
    
    while True:
        try:
            await update_bookings_to_checked_in()
        except Exception as e:
            logger.error(f"[BOOKING LIFECYCLE] Hourly scheduler error: {str(e)}")
        
        # Wait before next check
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    """
    Run directly for testing purposes.
    In production, this should be integrated with your application startup.
    """
    asyncio.run(run_hourly_booking_lifecycle_scheduler())
