from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notifications_management.notifications import (
    insert_notification_record,
    fetch_user_notifications,
    mark_as_read_record,
)
from app.models.sqlalchemy_schemas.notifications import Notifications


# ==========================================================
# 🔹 ADD NOTIFICATION
# ==========================================================

async def add_notification(db: AsyncSession, payload, commit: bool = True) -> Notifications:
    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)

    recipient_user_id = data.get("recipient_user_id") or data.get("resc_user_id")
    if recipient_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_user_id is required",
        )

    title = data.get("title")
    message = data.get("message")
    if not title or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title and message are required",
        )

    notification_payload = {
        "recipient_user_id": recipient_user_id,
        "notification_type": data.get("notification_type"),
        "entity_type": data.get("entity_type"),
        "entity_id": data.get("entity_id"),
        "title": title,
        "message": message,
    }

    try:
        obj = await insert_notification_record(db, notification_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )

    return obj


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
