from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.notifications import Notifications


async def add_notification(db: AsyncSession, payload, commit: bool = True) -> Notifications:
    """Create a notification record.

    payload is expected to be a Pydantic model (NotificationCreate) or an object
    with attributes matching the Notifications constructor.
    """
    data = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)

    # map alias used in pydantic model to the DB field name
    recipient_user_id = data.get("recipient_user_id") or data.get("resc_user_id")
    if recipient_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recipient_user_id is required")

    notification_type = data.get("notification_type")
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    title = data.get("title")
    message = data.get("message")

    if not title or not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title and message are required")

    obj = Notifications(
        recipient_user_id=recipient_user_id,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        message=message,
    )

    db.add(obj)
    # flush to assign PKs and emit INSERT within the current transaction
    await db.flush()

    if commit:
        await db.commit()
        await db.refresh(obj)

    return obj


async def list_user_notifications(
    db: AsyncSession,
    user_id: int,
    include_read: bool = True,
    include_deleted: bool = False,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
) -> List[Notifications]:
    """Return notifications for a recipient user ordered by created_at desc.

    - include_read: if False, filter out notifications where is_read==True
    - include_deleted: if False, filter out deleted notifications
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

    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def mark_notification_as_read(db: AsyncSession, notification_id: int, user_id: int) -> None:
    """Mark a notification as read. Only the recipient may mark their notification as read."""
    stmt = select(Notifications).where(Notifications.notification_id == notification_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if obj.recipient_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot mark another user's notification as read")

    obj.is_read = True
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {"message":"marked as read"}
