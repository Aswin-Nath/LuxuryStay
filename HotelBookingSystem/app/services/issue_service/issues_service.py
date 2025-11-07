import asyncio
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD imports
from app.crud.issues_management.issues import (
    insert_issue,
    get_issue_by_id,
    update_issue_fields,
    list_issues_records,
    get_issue_images,
    insert_chat_message,
    list_chat_messages,
)

# External services
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.room_service.images_service import create_image
from app.services.notification_service.notifications_service import add_notification
from app.schemas.pydantic_models.notifications import NotificationCreate


# ==========================================================
# 🔹 CREATE ISSUE
# ==========================================================

async def create_issue(
    db: AsyncSession,
    payload: dict,
    images: Optional[List[UploadFile]] = None,
) -> dict:
    issue = await insert_issue(
        db,
        {
            "booking_id": payload["booking_id"],
            "room_id": payload.get("room_id"),
            "user_id": payload["user_id"],
            "title": payload["title"],
            "description": payload["description"],
        },
    )

    if images:
        try:
            upload_tasks = [save_uploaded_image(f) for f in images]
            uploaded_urls = await asyncio.gather(*upload_tasks, return_exceptions=True)

            for result in uploaded_urls:
                if isinstance(result, Exception):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Image upload failed: {result}",
                    )
                await create_image(
                    db,
                    entity_type="issue",
                    entity_id=issue.issue_id,
                    image_url=str(result),
                    uploaded_by=payload["user_id"],
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image handling failed: {e}")

    # Add notification
    try:
        notif = NotificationCreate(
            recipient_user_id=issue.user_id,
            notification_type="SYSTEM",
            entity_type="ISSUE",
            entity_id=issue.issue_id,
            title="Issue created",
            message=f"Your issue #{issue.issue_id} has been created. Title: {issue.title}",
        )
        await add_notification(db, notif, commit=True)
    except Exception:
        await db.rollback()

    await db.refresh(issue)
    db.expunge(issue)
    return issue


# ==========================================================
# 🔹 GET ISSUE
# ==========================================================

async def get_issue(db: AsyncSession, issue_id: int):
    issue = await get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    images = await get_issue_images(db, issue_id)
    issue.__dict__["images"] = images
    return issue


# ==========================================================
# 🔹 LIST ISSUES
# ==========================================================

async def list_issues(db: AsyncSession, user_id: Optional[int] = None, limit: int = 50, offset: int = 0):
    items = await list_issues_records(db, user_id, limit, offset)
    for issue in items:
        imgs = await get_issue_images(db, issue.issue_id)
        issue.__dict__["images"] = imgs
    return items


# ==========================================================
# 🔹 UPDATE ISSUE
# ==========================================================

async def update_issue(
    db: AsyncSession,
    issue_id: int,
    payload: dict,
    images: Optional[List[UploadFile]] = None,
):
    issue = await get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue = await update_issue_fields(db, issue, payload)

    if images:
        try:
            upload_tasks = [save_uploaded_image(f) for f in images]
            uploaded_urls = await asyncio.gather(*upload_tasks, return_exceptions=True)
            for result in uploaded_urls:
                if isinstance(result, Exception):
                    raise HTTPException(status_code=502, detail=f"Image upload failed: {result}")
                await create_image(
                    db,
                    entity_type="issue",
                    entity_id=issue.issue_id,
                    image_url=str(result),
                    uploaded_by=payload.get("user_id"),
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image handling failed: {e}")

    await db.refresh(issue)
    return issue


# ==========================================================
# 🔹 ADD CHAT
# ==========================================================

async def add_chat(db: AsyncSession, issue_id: int, sender_id: int, message: str):
    chat = await insert_chat_message(db, issue_id, sender_id, message)

    # Notify issue owner if sender isn’t them
    issue = await get_issue_by_id(db, issue_id)
    if issue and issue.user_id and issue.user_id != sender_id:
        notif = NotificationCreate(
            recipient_user_id=issue.user_id,
            notification_type="SYSTEM",
            entity_type="ISSUE",
            entity_id=issue_id,
            title="New message on your issue",
            message=f"New message on issue #{issue_id}: {message}",
        )
        await add_notification(db, notif)
    return chat


# ==========================================================
# 🔹 LIST CHATS
# ==========================================================

async def list_chats(db: AsyncSession, issue_id: int):
    return await list_chat_messages(db, issue_id)
