import asyncio
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD imports
from app.crud.issues import (
    insert_issue,
    get_issue_by_id,
    update_issue_fields,
    list_issues_records,
    get_issue_images,
    insert_chat_message,
    list_chat_messages,
)

# External services
from app.services.image_upload_service import save_uploaded_image
from app.utils.images_util import create_image
from app.services.notifications_service import add_notification
from app.schemas.pydantic_models.notifications import NotificationCreate


# ==========================================================
# 🔹 CREATE ISSUE
# ==========================================================

async def create_issue(
    db: AsyncSession,
    payload: dict,
    images: Optional[List[UploadFile]] = None,
) -> dict:
    """
    Create a new issue/bug report with optional images.
    
    Creates an issue record for a booking with title, description, and optional attached images.
    Automatically generates and sends a system notification to the issue creator. Images are
    uploaded asynchronously and linked to the issue via image records.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        payload (dict): Issue data including booking_id, user_id, title, description, room_id (optional).
        images (Optional[List[UploadFile]]): List of image files to attach (default None).
    
    Returns:
        dict: The newly created issue record with issue_id and timestamps.
    
    Raises:
        HTTPException (502): If image upload fails.
        HTTPException (500): If image handling or database operations fail.
    
    Side Effects:
        - Creates issue record
        - Uploads and saves images if provided
        - Creates image entity records linking to issue
        - Sends notification to issue creator
    """
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
    """
    Retrieve a single issue with its attached images.
    
    Fetches an issue record by ID and eagerly loads all associated images. Returns
    complete issue details for displaying to users or admin.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        issue_id (int): The ID of the issue to retrieve.
    
    Returns:
        dict: Issue record with images list in __dict__["images"].
    
    Raises:
        HTTPException (404): If issue not found.
    """
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
    """
    Retrieve list of issues with pagination and optional user filtering.
    
    Fetches issues with attached images for each one. Supports filtering by issue creator
    (user_id) and paginated results. Each issue includes all associated image URLs.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        user_id (Optional[int]): Filter issues by creator user ID (default None = all).
        limit (int): Maximum number of issues to return (default 50).
        offset (int): Number of issues to skip for pagination (default 0).
    
    Returns:
        list: List of issue records, each with images list populated in __dict__["images"].
    """
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
    """
    Update issue details and optionally add new images.
    
    Updates existing issue record with new title, description, or status. Can also attach
    additional images which are uploaded and linked to the issue. Does not delete existing images.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        issue_id (int): The ID of the issue to update.
        payload (dict): Updated issue fields (title, description, status, etc.).
        images (Optional[List[UploadFile]]): Additional images to attach (default None).
    
    Returns:
        dict: Updated issue record with new data and timestamps.
    
    Raises:
        HTTPException (404): If issue not found.
        HTTPException (502): If image upload fails.
        HTTPException (500): If image handling or database operations fail.
    """
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
    """
    Add a message to an issue's discussion thread.
    
    Creates a chat message associated with an issue for collaborative communication. Automatically
    notifies the issue owner if the sender is not the original issue creator.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        issue_id (int): The ID of the issue to comment on.
        sender_id (int): The user ID of the message sender.
        message (str): The chat message content.
    
    Returns:
        dict: The newly created chat message record with timestamps and sender info.
    
    Side Effects:
        - Sends notification to issue owner if sender is not the creator
    """
    chat = await insert_chat_message(db, issue_id, sender_id, message)

    # Notify issue owner if sender isn't them
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
    """
    Retrieve all chat messages for an issue.
    
    Fetches the complete discussion thread for an issue, ordered chronologically.
    Includes all messages exchanged between users and support staff regarding the issue.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        issue_id (int): The ID of the issue.
    
    Returns:
        list: All chat message records for the issue, ordered by timestamp.
    """
    return await list_chat_messages(db, issue_id)
