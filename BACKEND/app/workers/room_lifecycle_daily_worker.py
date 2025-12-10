"""
11:59 PM worker for completing booking and room lifecycle.

This worker runs at 11:59 PM daily to:
1. Find all bookings with status 'Checked-In' where check_out date is today
2. Update booking status from 'Checked-In' to 'Checked-Out'
3. Update room status of all rooms in that booking from 'BOOKED' (occupied) to 'AVAILABLE'

This ensures that when a guest's checkout date arrives (end of day), their booking is
automatically marked as checked-out and rooms are made available for the next booking.
"""

from datetime import datetime, date
from sqlalchemy import select
import asyncio
import logging

from app.models.sqlalchemy_schemas.bookings import Bookings, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import RoomStatus
from app.database.postgres_connection import AsyncSessionLocal

# Setup logging
logger = logging.getLogger(__name__)



async def update_bookings_to_checked_out():
    """
    Check for bookings with status 'Checked-In' where check_out date is today.
    Update their status to 'Checked-Out' and mark associated rooms as 'AVAILABLE'.
    
    Process:
    1. Get today's date
    2. Find all bookings where:
       - status = 'Checked-In'
       - check_out = today's date
       - is_deleted = false
    3. For each booking:
       - Update booking.status = 'Checked-Out'
       - Get all rooms in that booking via BookingRoomMap
       - Update each room's room_status = 'AVAILABLE'
    4. Commit changes
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get today's date (without time)
            today = date.today()
            
            # ========== FIND ALL CHECKED-IN BOOKINGS WITH TODAY AS CHECK-OUT ==========
            query = await db.execute(
                select(Bookings).where(
                    Bookings.status == "Checked-In",
                    Bookings.check_out == today,
                    Bookings.is_deleted.is_(False)
                )
            )
            bookings_to_check_out = query.scalars().all()
            
            if not bookings_to_check_out:
                logger.info("[ROOM LIFECYCLE] No checked-in bookings with checkout today")
                return
            
            logger.info(
                f"[ROOM LIFECYCLE] Found {len(bookings_to_check_out)} booking(s) to check out"
            )
            
            # ========== UPDATE BOOKINGS AND ASSOCIATED ROOMS ==========
            checked_out_count = 0
            rooms_available_count = 0
            
            for booking in bookings_to_check_out:
                try:
                    # Update booking status to Checked-Out
                    booking.status = "Checked-Out"
                    checked_out_count += 1
                    
                    logger.info(
                        f"[ROOM LIFECYCLE] Booking {booking.booking_id}: "
                        f"status updated to 'Checked-Out'"
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
                        # Update room status to AVAILABLE
                        room = room_map.room
                        if room:
                            room.room_status = RoomStatus.AVAILABLE
                            rooms_available_count += 1
                            
                            logger.info(
                                f"[ROOM LIFECYCLE] Room {room.room_id} (Room No: {room.room_no}): "
                                f"status updated to 'AVAILABLE'"
                            )
                
                except Exception as e:
                    logger.error(
                        f"[ROOM LIFECYCLE] Error processing booking {booking.booking_id}: {str(e)}"
                    )
                    await db.rollback()
                    raise
            
            # ========== COMMIT CHANGES ==========
            await db.commit()
            
            logger.info(
                f"[ROOM LIFECYCLE] Successfully updated {checked_out_count} booking(s) to 'Checked-Out' "
                f"and marked {rooms_available_count} room(s) as 'AVAILABLE'"
            )
            
        except Exception as e:
            logger.error(f"[ROOM LIFECYCLE] Error in 11:59 PM checkout update: {str(e)}")
            await db.rollback()
            raise


async def run_daily_checkout_scheduler_at_1159pm():
    """
    Run the checkout update task at 11:59 PM every day.
    
    This scheduler calculates the time until the next 11:59 PM and waits,
    then executes the checkout logic. After execution, it calculates the
    time until the next day's 11:59 PM.
    
    This should be started as a background task when the application starts.
    """
    logger.info("[ROOM LIFECYCLE] Daily checkout scheduler (11:59 PM) started")
    
    while True:
        try:
            # Calculate time until next 11:59 PM
            now = datetime.now()
            target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
            
            # If we've already passed 11:59 PM today, schedule for tomorrow
            if now >= target_time:
                target_time = target_time.replace(day=target_time.day + 1) if target_time.day < 28 else target_time.replace(day=1, month=target_time.month + 1)
                # Handle month/year transition
                if target_time.month > 12:
                    target_time = target_time.replace(month=1, year=target_time.year + 1)
            
            # Calculate seconds to wait
            time_diff = (target_time - now).total_seconds()
            
            logger.info(
                f"[ROOM LIFECYCLE] Waiting {time_diff:.0f} seconds until next checkout at 11:59 PM"
            )
            
            # Wait until 11:59 PM
            await asyncio.sleep(time_diff)
            
            # Execute checkout logic
            logger.info("[ROOM LIFECYCLE] Executing 11:59 PM checkout process")
            await update_bookings_to_checked_out()
            
        except Exception as e:
            logger.error(f"[ROOM LIFECYCLE] Daily checkout scheduler error: {str(e)}")
            # Wait 60 seconds before retrying to avoid tight error loops
            await asyncio.sleep(60)


if __name__ == "__main__":
    """
    Run directly for testing purposes.
    In production, this should be integrated with your application startup.
    """
    asyncio.run(run_daily_checkout_scheduler_at_1159pm())
