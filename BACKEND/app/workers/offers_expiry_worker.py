"""
11:59 PM worker for deactivating expired offers.

This worker runs at 11:59 PM daily to:
1. Find all offers where valid_to date is today or in the past
2. Mark those offers as is_active = False
3. Log the deactivation for audit purposes

This ensures that offers automatically expire at the end of their validity period
without manual intervention, providing a clean and automated offer lifecycle management.
"""

from datetime import datetime, date
from sqlalchemy import select
import asyncio
import logging

from app.models.sqlalchemy_schemas.offers import Offers
from app.database.postgres_connection import AsyncSessionLocal

# Setup logging
logger = logging.getLogger(__name__)


async def deactivate_expired_offers():
    """
    Check for offers with valid_to date as today or earlier.
    Update their is_active status to False.
    
    Process:
    1. Get today's date
    2. Find all offers where:
       - valid_to <= today's date
       - is_active = true
       - is_deleted = false
    3. For each offer:
       - Update offer.is_active = False
       - Log the deactivation
    4. Commit changes
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get today's date (without time)
            today = date.today()
            
            # ========== FIND ALL ACTIVE OFFERS THAT HAVE EXPIRED ==========
            query = await db.execute(
                select(Offers).where(
                    Offers.valid_to <= today,
                    Offers.is_active.is_(True),
                    Offers.is_deleted.is_(False)
                )
            )
            expired_offers = query.scalars().all()
            
            if not expired_offers:
                logger.info("[OFFER EXPIRY] No expired offers to deactivate today")
                return
            
            logger.info(
                f"[OFFER EXPIRY] Found {len(expired_offers)} offer(s) to deactivate"
            )
            
            # ========== DEACTIVATE EXPIRED OFFERS ==========
            deactivated_count = 0
            
            for offer in expired_offers:
                try:
                    # Update offer is_active to False
                    offer.is_active = False
                    deactivated_count += 1
                    
                    logger.info(
                        f"[OFFER EXPIRY] Offer {offer.offer_id} ({offer.offer_name}): "
                        f"marked as inactive (valid_to: {offer.valid_to})"
                    )
                    
                except Exception as offer_error:
                    logger.error(
                        f"[OFFER EXPIRY] Error deactivating offer {offer.offer_id}: {str(offer_error)}"
                    )
                    continue
            
            # ========== COMMIT CHANGES ==========
            if deactivated_count > 0:
                await db.commit()
                logger.info(
                    f"[OFFER EXPIRY] Successfully deactivated {deactivated_count} offer(s)"
                )
            else:
                logger.info("[OFFER EXPIRY] No offers were deactivated")
                
        except Exception as error:
            logger.error(f"[OFFER EXPIRY] Worker error: {str(error)}", exc_info=True)
            await db.rollback()


async def run_offer_expiry_scheduler_at_1159pm():
    """
    Run the offer expiry checker daily at 11:59 PM.
    
    This scheduler:
    1. Calculates time until 11:59 PM
    2. Sleeps until 11:59 PM
    3. Runs the deactivation logic
    4. Waits 24 hours before repeating
    
    The timing ensures offers are deactivated at the very end of their last valid day.
    """
    while True:
        try:
            now = datetime.now()
            target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
            
            # If it's already past 11:59 PM today, target tomorrow's 11:59 PM
            if now > target_time:
                target_time = target_time.replace(day=target_time.day + 1) if target_time.day < 28 else target_time.replace(day=1, month=target_time.month + 1)
            
            # Calculate sleep duration
            sleep_seconds = (target_time - now).total_seconds()
            
            logger.info(
                f"[OFFER EXPIRY] Scheduler sleeping for {sleep_seconds:.0f} seconds "
                f"(next run: {target_time.strftime('%Y-%m-%d %H:%M:%S')})"
            )
            
            # Sleep until the target time
            await asyncio.sleep(sleep_seconds)
            
            # Run the deactivation logic
            logger.info("[OFFER EXPIRY] Running offer expiry check at 11:59 PM")
            await deactivate_expired_offers()
            
            # Wait for the next day (24 hours from now)
            await asyncio.sleep(60)  # Sleep for 1 minute to avoid running multiple times in the same minute
            
        except asyncio.CancelledError:
            logger.info("[OFFER EXPIRY] Scheduler was cancelled")
            break
        except Exception as error:
            logger.error(f"[OFFER EXPIRY] Scheduler error: {str(error)}", exc_info=True)
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)
