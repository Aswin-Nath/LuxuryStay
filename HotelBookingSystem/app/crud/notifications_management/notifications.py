from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.notifications import Notifications


# ==========================================================
# 🔹 CREATE NOTIFICATION
# ==========================================================

async def insert_notification_record(db: AsyncSession, payload: dict) -> Notifications:
    """
    Create and persist a new notification record.
    
    Inserts a notification into the database and immediately commits and refreshes it
    to populate database-generated fields like notification_id and created_at.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        payload (dict): Notification data including recipient_user_id, title, message,
                       notification_type, entity_type, entity_id.
    
    Returns:
        Notifications: The newly created notification record with all fields populated.
    """
    notification_record = Notifications(**payload)
    db.add(notification_record)
    await db.flush()
    await db.commit()
    await db.refresh(notification_record)
    return notification_record


# ==========================================================
# 🔹 FETCH NOTIFICATIONS
# ==========================================================

async def fetch_user_notifications(
    db: AsyncSession,
    user_id: int,
    include_read: bool = True,
    include_deleted: bool = False,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
) -> List[Notifications]:
    """
    Retrieve notifications for a user with conditional filtering.
    
    Fetches notifications for a specific recipient, optionally filtering by read status and
    soft-delete flag. Results are ordered by most recent created_at first and paginated.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The recipient user ID to filter by.
        include_read (bool): If False, excludes already-read notifications (default True).
        include_deleted (bool): If False, excludes soft-deleted notifications (default False).
        limit (Optional[int]): Maximum number of records to return (default 50).
        offset (Optional[int]): Number of records to skip for pagination (default 0).
    
    Returns:
        List[Notifications]: Notifications ordered by created_at DESC, matching all filters.
    """
    stmt = select(Notifications).where(Notifications.recipient_user_id == user_id)
    if not include_read:
        stmt = stmt.where(Notifications.is_read == False)
    if not include_deleted:
        stmt = stmt.where(Notifications.is_deleted == False)
    stmt = stmt.order_by(desc(Notifications.created_at))
    if limit:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


# ==========================================================
# 🔹 MARK AS READ
# ==========================================================

async def mark_as_read_record(db: AsyncSession, notification_id: int) -> Notifications:
    """
    Retrieve a notification by ID for marking as read.
    
    Fetches a single notification record by its notification_id. Used before
    updating the is_read flag. Called by service layer for ownership validation.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        notification_id (int): The ID of the notification to retrieve.
    
    Returns:
        Optional[Notifications]: The notification record if found, None otherwise.
    """
    stmt = select(Notifications).where(Notifications.notification_id == notification_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()
