# ==============================================================
# app/workers/booking_session_cleanup.py
# Purpose: Background worker to cleanup expired booking locks
#          and release rooms after 15-minute session timeout
# Runs: Every 30 seconds via APScheduler
# ==============================================================

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.sqlalchemy_schemas.rooms import (
    RoomAvailabilityLocks,
    Rooms,
    RoomStatus
)

logger = logging.getLogger(__name__)


class BookingSessionCleanupWorker:
    """
    Cleans up expired booking session locks every 30 seconds.
    Releases rooms and removes expired lock records.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = None
        self.SessionLocal = None

    async def initialize(self):
        """Initialize async engine and session factory."""
        self.engine = create_async_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def cleanup_expired_locks(self):
        """
        Run cleanup task - delete expired locks and free up rooms.
        Called every 30 seconds.
        """
        if not self.SessionLocal:
            logger.error("Worker not initialized")
            return

        db: AsyncSession = self.SessionLocal()
        try:
            now = datetime.utcnow()
            
            # 1. Find all EXPIRED locks (expires_at < NOW)
            result = await db.execute(
                select(RoomAvailabilityLocks).where(
                    RoomAvailabilityLocks.expires_at < now
                )
            )
            expired_locks = result.scalars().all()

            if not expired_locks:
                logger.debug(f"[BOOKING CLEANUP] No expired locks at {now.isoformat()}")
                return

            expired_count = len(expired_locks)
            logger.info(f"[BOOKING CLEANUP] Found {expired_count} expired locks")

            # 2. For each expired lock, release the room
            released_rooms = []
            for lock in expired_locks:
                try:
                    # Update room status to AVAILABLE
                    room = await db.get(Rooms, lock.room_id)
                    if room:
                        old_status = room.room_status
                        room.room_status = RoomStatus.AVAILABLE
                        await db.merge(room)
                        
                        released_rooms.append({
                            "lock_id": lock.lock_id,
                            "room_id": lock.room_id,
                            "room_no": room.room_no,
                            "user_id": lock.user_id,
                            "old_status": old_status.value,
                            "new_status": RoomStatus.AVAILABLE.value
                        })
                        logger.debug(
                            f"  → Released room {room.room_no} "
                            f"(was {old_status.value}, now AVAILABLE)"
                        )
                except Exception as e:
                    logger.error(f"  ✗ Error releasing room {lock.room_id}: {str(e)}")

            # 3. Delete expired locks
            await db.execute(
                delete(RoomAvailabilityLocks).where(
                    RoomAvailabilityLocks.expires_at < now
                )
            )

            await db.commit()

            # Log summary
            logger.info(
                f"[BOOKING CLEANUP] "
                f"Released {len(released_rooms)} rooms, "
                f"deleted {expired_count} locks"
            )

            return {
                "timestamp": now.isoformat(),
                "expired_locks_count": expired_count,
                "released_rooms": released_rooms
            }

        except Exception as e:
            logger.error(f"[BOOKING CLEANUP] Error: {str(e)}", exc_info=True)
            await db.rollback()
            raise
        finally:
            await db.close()

    async def cleanup_stale_payments(self):
        """
        Optional: Cleanup stale payment records.
        If using booking_payments table, delete payments that:
        - Status = 'pending'
        - updated_at < NOW - 15 minutes (payment session expired)
        - Release associated locks
        """
        logger.debug("[PAYMENT CLEANUP] Feature not yet implemented")
        pass

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()


# =============================================================
# APScheduler Integration (call from main.py)
# =============================================================

async def start_booking_cleanup_scheduler(db_url: str):
    """
    Start the background worker scheduler.
    Add this to main.py startup event.
    
    Usage in main.py:
    
    from app.workers.booking_session_cleanup import start_booking_cleanup_scheduler
    
    @app.on_event("startup")
    async def startup():
        asyncio.create_task(start_booking_cleanup_scheduler(DATABASE_URL))
    
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    
    worker = BookingSessionCleanupWorker(db_url)
    await worker.initialize()
    
    scheduler = AsyncIOScheduler()
    
    # Run cleanup every 30 seconds
    scheduler.add_job(
        worker.cleanup_expired_locks,
        'interval',
        seconds=30,
        id='booking_lock_cleanup',
        name='Cleanup expired booking locks',
        replace_existing=True
    )
    
    # Optional: Run payment cleanup every 60 seconds
    # scheduler.add_job(
    #     worker.cleanup_stale_payments,
    #     'interval',
    #     seconds=60,
    #     id='payment_cleanup',
    #     name='Cleanup stale payment records',
    #     replace_existing=True
    # )
    
    scheduler.start()
    logger.info("✅ [BOOKING WORKER] Scheduler started - running cleanup every 30 seconds")
    
    return scheduler
