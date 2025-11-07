from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.notifications import Notifications


# ==========================================================
# 🔹 CREATE NOTIFICATION
# ==========================================================

async def insert_notification_record(db: AsyncSession, payload: dict) -> Notifications:
    obj = Notifications(**payload)
    db.add(obj)
    await db.flush()
    await db.commit()
    await db.refresh(obj)
    return obj


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
    return res.scalars().all()


# ==========================================================
# 🔹 MARK AS READ
# ==========================================================

async def mark_as_read_record(db: AsyncSession, notification_id: int) -> Notifications:
    stmt = select(Notifications).where(Notifications.notification_id == notification_id)
    res = await db.execute(stmt)
    return res.scalars().first()
