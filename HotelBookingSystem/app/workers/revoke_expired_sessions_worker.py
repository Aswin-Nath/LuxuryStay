"""
Background worker for revoking expired sessions.

This worker runs periodically (every minute recommended) to:
1. Find all active sessions whose access_token_expires_at < current_time
2. Mark these sessions as revoked with reason AUTOMATIC_EXPIRED
3. Add their tokens to the blacklist

This ensures that expired sessions are automatically revoked and their tokens
cannot be used to make authenticated requests, maintaining security.
"""

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio
import logging

from app.models.sqlalchemy_schemas.authentication import (
    Sessions,
    BlacklistedTokens,
    RevokedType,
    TokenType,
)
from app.database.postgres_connection import DATABASE_URL

# Setup logging
logger = logging.getLogger(__name__)

# ========== DATABASE CONNECTION SETUP ==========
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def revoke_expired_sessions():
    """
    Revoke all sessions whose access tokens have expired.
    
    Queries for all sessions with:
    - is_active = true
    - access_token_expires_at < current_utc_time
    - revoked_at IS NULL
    
    Updates them to:
    - is_active = false
    - revoked_at = current_utc_time
    - revoked_reason = "Token expired"
    
    Also blacklists the access tokens and refresh tokens for these sessions.
    
    This prevents expired sessions from being used for authentication.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get current UTC time
            now_utc = datetime.utcnow()
            
            # ========== FIND ALL EXPIRED ACTIVE SESSIONS ==========
            query = await db.execute(
                select(Sessions).where(
                    Sessions.is_active == True,
                    Sessions.access_token_expires_at < now_utc,
                    Sessions.revoked_at == None,
                )
            )
            expired_sessions = query.scalars().all()
            
            if not expired_sessions:
                logger.info("[SESSION REVOKE] No expired sessions to revoke")
                return
            
            logger.info(f"[SESSION REVOKE] Found {len(expired_sessions)} expired session(s) to revoke")
            
            # ========== REVOKE EXPIRED SESSIONS ==========
            revoked_count = 0
            for session in expired_sessions:
                logger.info(
                    f"[SESSION REVOKE] Revoking session_id={session.session_id} "
                    f"for user_id={session.user_id} "
                    f"(access token expired at {session.access_token_expires_at})"
                )
                
                session.is_active = False
                session.revoked_at = now_utc
                session.revoked_reason = "Token expired"
                revoked_count += 1
                
                # ========== BLACKLIST ACCESS TOKEN ==========
                access_token_blacklist = BlacklistedTokens(
                    user_id=session.user_id,
                    session_id=session.session_id,
                    token_type=TokenType.ACCESS,
                    token_value_hash=session.access_token,  # In production, store hash instead of raw token
                    revoked_type=RevokedType.AUTOMATIC_EXPIRED,
                    reason="Access token automatically expired",
                    revoked_at=now_utc,
                )
                db.add(access_token_blacklist)
                
                # ========== BLACKLIST REFRESH TOKEN ==========
                refresh_token_blacklist = BlacklistedTokens(
                    user_id=session.user_id,
                    session_id=session.session_id,
                    token_type=TokenType.REFRESH,
                    token_value_hash=session.refresh_token,  # In production, store hash instead of raw token
                    revoked_type=RevokedType.AUTOMATIC_EXPIRED,
                    reason="Refresh token automatically expired",
                    revoked_at=now_utc,
                )
                db.add(refresh_token_blacklist)
            
            # ========== COMMIT CHANGES ==========
            await db.commit()
            
            logger.info(
                f"[SESSION REVOKE] Successfully revoked {revoked_count} expired session(s) "
                f"and blacklisted {revoked_count * 2} token(s)"
            )
            
        except Exception as e:
            logger.error(f"[SESSION REVOKE] Error revoking expired sessions: {str(e)}")
            await db.rollback()
            raise


async def run_session_revoke_scheduler(interval_seconds: int = 60):
    """
    Run the session revoke task on a schedule.
    
    Args:
        interval_seconds (int): How often to check for expired sessions (default: 60 seconds)
    
    This should be started as a background task when the application starts.
    """
    logger.info(f"[SESSION REVOKE] Scheduler started with {interval_seconds}s interval")
    
    while True:
        try:
            await revoke_expired_sessions()
        except Exception as e:
            logger.error(f"[SESSION REVOKE] Scheduler error: {str(e)}")
        
        # Wait before next check
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    """
    Run directly for testing purposes.
    In production, this should be integrated with your application startup.
    """
    asyncio.run(run_session_revoke_scheduler())
