from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, UploadFile
import asyncio

from app.models.sqlalchemy_schemas.issues import Issues, IssueChat
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.room_service.images_service import create_image
from app.models.pydantic_models.notifications import NotificationCreate
from app.services.notification_service.notifications_service import add_notification as svc_add_notification


# ===========================================================
# CREATE ISSUE
# ===========================================================
async def create_issue(db: AsyncSession, payload: dict, images: Optional[List[UploadFile]] = None) -> Issues:
    """
    payload: booking_id, room_id, user_id, title, description
    images: list of UploadFile objects (optional)
    """

    issue = Issues(
        booking_id=payload["booking_id"],
        room_id=payload.get("room_id"),
        user_id=payload["user_id"],
        title=payload["title"],
        description=payload["description"],
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    # Upload and link images (if any)
    if images:
        try:
            # upload concurrently
            coros = [save_uploaded_image(f) for f in images]
            upload_results = await asyncio.gather(*coros, return_exceptions=True)

            image_ids = []
            for result in upload_results:
                if isinstance(result, Exception):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Image upload failed: {result}",
                    )
                img = await create_image(
                    db,
                    entity_type="issue",
                    entity_id=issue.issue_id,
                    image_url=str(result),
                    uploaded_by=payload["user_id"],
                )
                image_ids.append(img.image_id)
            issue.images = image_ids
            await db.commit()
            await db.refresh(issue)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image handling failed: {e}")

    # Notify issue creator
    try:
        notif = NotificationCreate(
            recipient_user_id=issue.user_id,
            notification_type="SYSTEM",
            entity_type="ISSUE",
            entity_id=issue.issue_id,
            title="Issue created",
            message=f"Your issue #{issue.issue_id} has been created. Title: {issue.title}",
        )
        await svc_add_notification(db, notif, commit=False)
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass

    return issue


# ===========================================================
# GET ISSUE
# ===========================================================
async def get_issue(db: AsyncSession, issue_id: int) -> Issues:
    stmt = select(Issues).where(Issues.issue_id == issue_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return obj


# ===========================================================
# LIST ISSUES
# ===========================================================
async def list_issues(db: AsyncSession, user_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Issues]:
    stmt = select(Issues).limit(limit).offset(offset)
    if user_id is not None:
        stmt = stmt.where(Issues.user_id == user_id)
    res = await db.execute(stmt)
    return res.scalars().all()


# ===========================================================
# UPDATE ISSUE
# ===========================================================
async def update_issue(
    db: AsyncSession,
    issue_id: int,
    payload: dict,
    images: Optional[List[UploadFile]] = None,
) -> Issues:
    """
    Update issue fields and optionally replace images.
    If images are provided, uploads and replaces linked images.
    """
    stmt = select(Issues).where(Issues.issue_id == issue_id)
    res = await db.execute(stmt)
    issue = res.scalars().first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Update scalar fields
    for k in ("booking_id", "room_id", "title", "description", "status", "resolved_by"):
        if k in payload and payload.get(k) is not None:
            setattr(issue, k, payload.get(k))

    # Replace images if provided
    if images is not None:
        try:
            coros = [save_uploaded_image(f) for f in images]
            upload_results = await asyncio.gather(*coros, return_exceptions=True)

            image_ids = []
            for result in upload_results:
                if isinstance(result, Exception):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Image upload failed: {result}",
                    )
                img = await create_image(
                    db,
                    entity_type="issue",
                    entity_id=issue.issue_id,
                    image_url=str(result),
                    uploaded_by=payload.get("user_id"),
                )
                image_ids.append(img.image_id)
            issue.images = image_ids
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image handling failed: {e}")

    await db.commit()
    await db.refresh(issue)
    return issue


# ===========================================================
# ADD CHAT MESSAGE
# ===========================================================
async def add_chat(db: AsyncSession, issue_id: int, sender_id: int, message: str):
    chat = IssueChat(issue_id=issue_id, sender_id=sender_id, message=message)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

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
        pass

    return chat


# ===========================================================
# LIST CHATS
# ===========================================================
async def list_chats(db: AsyncSession, issue_id: int):
    res = await db.execute(
        select(IssueChat)
        .where(IssueChat.issue_id == issue_id)
        .order_by(IssueChat.sent_at)
    )
    return res.scalars().all()
