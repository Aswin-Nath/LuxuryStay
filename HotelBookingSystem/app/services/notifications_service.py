from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notifications import (
    insert_notification_record,
    fetch_user_notifications,
    mark_as_read_record,
)
from app.models.sqlalchemy_schemas.notifications import Notifications


# ==========================================================
# 🔹 ADD NOTIFICATION
# ==========================================================

async def add_notification(db: AsyncSession, payload, commit: bool = True) -> Notifications:
    """
    Create a new notification for a recipient user.
    
    Validates required fields (recipient_user_id, title, message) and creates a notification
    record with optional entity references (e.g., booking_id, room_id). Notification types
    can be BOOKING, REFUND, OFFER, REVIEW, etc.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        payload: Pydantic model containing recipient_user_id, title, message, notification_type,
                 entity_type, entity_id.
        commit (bool): Whether to commit changes (default True).
    
    Returns:
        Notifications: The newly created notification record.
    
    Raises:
        HTTPException (400): If recipient_user_id, title, or message is missing.
        HTTPException (500): If database insert fails.
    """
    notification_data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)

    recipient_user_id = notification_data.get("recipient_user_id") or notification_data.get("resc_user_id")
    if recipient_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_user_id is required",
        )

    title = notification_data.get("title")
    message = notification_data.get("message")
    if not title or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title and message are required",
        )

    notification_payload = {
        "recipient_user_id": recipient_user_id,
        "notification_type": notification_data.get("notification_type"),
        "entity_type": notification_data.get("entity_type"),
        "entity_id": notification_data.get("entity_id"),
        "title": title,
        "message": message,
    }

    try:
        notification_record = await insert_notification_record(db, notification_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )

    return notification_record


# ==========================================================
# 🔹 LIST USER NOTIFICATIONS
# ==========================================================

async def list_user_notifications(
    db: AsyncSession,
    user_id: int,
    include_read: bool = True,
    include_deleted: bool = False,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
) -> List[Notifications]:
    """
    Retrieve notifications for a specific user with optional filtering.
    
    Fetches user notifications with support for including/excluding read and soft-deleted
    notifications. Results are sorted by most recent and paginated.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The ID of the recipient user.
        include_read (bool): Whether to include already-read notifications (default True).
        include_deleted (bool): Whether to include soft-deleted notifications (default False).
        limit (Optional[int]): Maximum number of records to return (default 50).
        offset (Optional[int]): Number of records to skip for pagination (default 0).
    
    Returns:
        List[Notifications]: List of notification records for the user, sorted newest first.
    """
    notifications = await fetch_user_notifications(
        db,
        user_id=user_id,
        include_read=include_read,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    return notifications


# ==========================================================
# 🔹 MARK NOTIFICATION AS READ
# ==========================================================

async def mark_notification_as_read(db: AsyncSession, notification_id: int, user_id: int):
    """
    Mark a notification as read by the recipient user.
    
    Sets the is_read flag on a notification record. Validates that the current user
    is the notification recipient (ownership check).
    
    Args:
        db (AsyncSession): Database session for executing the query.
        notification_id (int): The ID of the notification to mark as read.
        user_id (int): The ID of the current user (must be notification recipient).
    
    Returns:
        dict: Message confirmation {"message": "marked as read"}.
    
    Raises:
        HTTPException (404): If notification not found.
        HTTPException (403): If user is not the notification recipient.
    """
    notification = await mark_as_read_record(db, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.recipient_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot mark another user's notification as read",
        )

    notification.is_read = True
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    return {"message": "marked as read"}
