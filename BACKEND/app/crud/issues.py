from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.issues import Issues, IssueChat
from app.models.sqlalchemy_schemas.images import Images


# ==========================================================
# 🔹 ISSUES CRUD
# ==========================================================

async def insert_issue(db: AsyncSession, payload: dict) -> Issues:
    issue = Issues(**payload)
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


async def get_issue_by_id(db: AsyncSession, issue_id: int) -> Optional[Issues]:
    stmt = select(Issues).where(Issues.issue_id == issue_id)
    query_result = await db.execute(stmt)
    return query_result.scalars().first()


async def update_issue_fields(db: AsyncSession, issue: Issues, payload: dict):
    for key, val in payload.items():
        if hasattr(issue, key) and val is not None:
            setattr(issue, key, val)
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


async def list_issues_records(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    room_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "recent",
    limit: int = 50,
    offset: int = 0,
) -> List[Issues]:
    """
    List issues with advanced filtering and sorting.
    
    Supports filtering by:
    - user_id: Filter by issue creator
    - status: OPEN, IN_PROGRESS, RESOLVED, CLOSED
    - room_id: Filter by room ID (checks if room_id is in room_ids array)
    - search: Search in title and description (case-insensitive)
    - date_from/date_to: Filter by reported_at date range
    - sort_by: recent (DESC), oldest (ASC), title (A-Z)
    """
    from datetime import datetime
    
    stmt = select(Issues)
    
    # Apply filters
    if user_id:
        stmt = stmt.where(Issues.user_id == user_id)
    
    if status:
        stmt = stmt.where(Issues.status == status)
    
    if room_id:
        # Filter issues where room_ids array contains the specified room_id
        stmt = stmt.where(Issues.room_ids.contains([room_id]))
    
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (Issues.title.ilike(search_pattern)) | (Issues.description.ilike(search_pattern))
        )
    
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            stmt = stmt.where(Issues.reported_at >= from_date)
        except ValueError:
            pass  # Invalid date format, skip filter
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            # Add 1 day to include entire day
            to_date = to_date.replace(hour=23, minute=59, second=59)
            stmt = stmt.where(Issues.reported_at <= to_date)
        except ValueError:
            pass  # Invalid date format, skip filter
    
    # Apply sorting
    if sort_by == "oldest":
        stmt = stmt.order_by(Issues.reported_at.asc())
    elif sort_by == "title":
        stmt = stmt.order_by(Issues.title.asc())
    else:  # recent (default)
        stmt = stmt.order_by(Issues.reported_at.desc())
    
    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)
    
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


# ==========================================================
# 🔹 IMAGES LINKING (used for hydration)
# ==========================================================

async def get_issue_images(db: AsyncSession, issue_id: int) -> List[Images]:
    stmt = (
        select(Images)
        .where(Images.entity_type == "issue")
        .where(Images.entity_id == issue_id)
        .where(Images.is_deleted.is_(False))
    )
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


# ==========================================================
# 🔹 CHAT CRUD
# ==========================================================

async def insert_chat_message(db: AsyncSession, issue_id: int, sender_id: int, message: str) -> IssueChat:
    chat = IssueChat(issue_id=issue_id, sender_id=sender_id, message=message)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def list_chat_messages(db: AsyncSession, issue_id: int) -> List[IssueChat]:
    stmt = (
        select(IssueChat)
        .where(IssueChat.issue_id == issue_id)
        .order_by(IssueChat.sent_at)
    )
    query_result = await db.execute(stmt)
    return query_result.scalars().all()
