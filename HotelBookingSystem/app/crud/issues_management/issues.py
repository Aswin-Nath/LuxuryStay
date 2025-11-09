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


async def list_issues_records(db: AsyncSession, user_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Issues]:
    stmt = select(Issues).limit(limit).offset(offset)
    if user_id:
        stmt = stmt.where(Issues.user_id == user_id)
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
