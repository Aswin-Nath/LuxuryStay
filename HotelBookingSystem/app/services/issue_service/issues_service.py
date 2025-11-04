from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.issues import Issues
from app.models.sqlalchemy_schemas.issues import IssueChat
from app.services.room_service.images_service import create_image
from app.models.pydantic_models.notifications import NotificationCreate
from app.services.notification_service.notifications_service import add_notification as svc_add_notification


async def create_issue(db: AsyncSession, payload: dict) -> Issues:
    # payload contains booking_id, room_id, user_id, title, description, images (list of urls)
    issue = Issues(
        booking_id=payload["booking_id"],
        room_id=payload.get("room_id"),
        user_id=payload["user_id"],
        title=payload["title"],
        description=payload["description"],
        images=payload.get("images", []),
    )
    db.add(issue)
    await db.commit()

    stmt = select(Issues).where(Issues.issue_id == issue.issue_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create issue")

    # If caller provided image URLs, create image rows and store their IDs
    image_urls = payload.get("images") or []
    if image_urls:
        image_ids = []
        for url in image_urls:
            img = await create_image(db, entity_type="issue", entity_id=obj.issue_id, image_url=url, uploaded_by=payload.get("user_id"))
            image_ids.append(img.image_id)
        obj.images = image_ids
        await db.commit()
        # refresh from DB to ensure latest data
        res = await db.execute(select(Issues).where(Issues.issue_id == obj.issue_id))
        obj = res.scalars().first()

    # Notify the issue creator that their issue was created
    try:
        notif = NotificationCreate(
            recipient_user_id=obj.user_id,
            notification_type="SYSTEM",
            entity_type="ISSUE",
            entity_id=obj.issue_id,
            title="Issue created",
            message=f"Your issue #{obj.issue_id} has been created. Title: {obj.title}",
        )
        # create notification without committing (so caller controls transaction)
        await svc_add_notification(db, notif, commit=False)
        # persist the notification (and any pending changes) now
        await db.commit()
    except Exception:
        # don't fail issue creation on notification errors
        try:
            await db.rollback()
        except Exception:
            pass
    return obj
    return obj


async def get_issue(db: AsyncSession, issue_id: int) -> Issues:
    stmt = select(Issues).where(Issues.issue_id == issue_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return obj


async def list_issues(db: AsyncSession, user_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Issues]:
    stmt = select(Issues).limit(limit).offset(offset)
    if user_id is not None:
        stmt = stmt.where(Issues.user_id == user_id)
    res = await db.execute(stmt)
    return res.scalars().all()


async def update_issue(db: AsyncSession, issue_id: int, payload: dict) -> Issues:
    stmt = select(Issues).where(Issues.issue_id == issue_id)
    res = await db.execute(stmt)
    issue = res.scalars().first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Update allowed fields (images require creating image rows when provided as URLs)
    for k in ("booking_id", "room_id", "title", "description", "status", "resolved_by"):
        if k in payload and payload.get(k) is not None:
            setattr(issue, k, payload.get(k))

    # Handle images separately: if provided, assume list of image URLs to create and replace current images
    if "images" in payload and payload.get("images") is not None:
        image_urls = payload.get("images") or []
        image_ids = []
        for url in image_urls:
            img = await create_image(db, entity_type="issue", entity_id=issue.issue_id, image_url=url, uploaded_by=payload.get("user_id"))
            image_ids.append(img.image_id)
        issue.images = image_ids

    await db.commit()

    res = await db.execute(select(Issues).where(Issues.issue_id == issue_id))
    return res.scalars().first()


async def add_chat(db: AsyncSession, issue_id: int, sender_id: int, message: str):
    chat = IssueChat(issue_id=issue_id, sender_id=sender_id, message=message)
    db.add(chat)
    await db.commit()
    res = await db.execute(select(IssueChat).where(IssueChat.chat_id == chat.chat_id))
    chat_obj = res.scalars().first()

    # Notify the issue owner if someone else sent the message
    try:
        issue_res = await db.execute(select(Issues).where(Issues.issue_id == issue_id))
        issue_obj = issue_res.scalars().first()
        if issue_obj and issue_obj.user_id and issue_obj.user_id != sender_id:
            notif = NotificationCreate(
                recipient_user_id=issue_obj.user_id,
                notification_type="SYSTEM",
                entity_type="ISSUE",
                entity_id=issue_id,
                title="New message on your issue",
                message=f"New message on issue #{issue_id}: {message}",
            )
            await svc_add_notification(db, notif)
    except Exception:
        # don't fail chat creation if notification errors occur
        pass

    return chat_obj


async def list_chats(db: AsyncSession, issue_id: int):
    res = await db.execute(select(IssueChat).where(IssueChat.issue_id == issue_id).order_by(IssueChat.sent_at))
    return res.scalars().all()
