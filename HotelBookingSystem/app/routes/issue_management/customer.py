from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.services.image_upload_service import save_uploaded_image
from app.services.issues_service import create_issue as svc_create_issue, list_issues as svc_list_issues, get_issue as svc_get_issue, update_issue as svc_update_issue, add_chat as svc_add_chat, list_chats as svc_list_chats
from app.models.pydantic_models.issues import IssueResponse, IssueCreate, IssueUpdate


router = APIRouter(prefix="/api/issues", tags=["ISSUES"])


@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    booking_id: int = Form(...),
    room_id: Optional[int] = Form(None),
    title: str = Form(...),
    description: str = Form(...),
    images: Optional[List[UploadFile]] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # upload images and collect URLs
    urls: List[str] = []
    if images:
        # upload concurrently
        coros = [save_uploaded_image(f) for f in images]
        results = await asyncio.gather(*coros, return_exceptions=True)
        # if any result is Exception, raise HTTP 502
        for r in results:
            if isinstance(r, Exception):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {r}")
        urls = [str(r) for r in results]

    payload = {
        "booking_id": booking_id,
        "room_id": room_id,
        "user_id": current_user.user_id,
        "title": title,
        "description": description,
        "images": urls,
    }

    obj = await svc_create_issue(db, payload)
    return IssueResponse.model_validate(obj).model_dump()


@router.get("/", response_model=List[IssueResponse])
async def list_my_issues(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    items = await svc_list_issues(db, user_id=current_user.user_id, limit=limit, offset=offset)
    return [IssueResponse.model_validate(i).model_dump() for i in items]


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_my_issue(issue_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_get_issue(db, issue_id)
    if obj.user_id != current_user.user_id:
        # forbid viewing others' issues
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to view this issue")
    return IssueResponse.model_validate(obj).model_dump()


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_my_issue(
    issue_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    obj = await svc_get_issue(db, issue_id)
    if obj.user_id != current_user.user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to edit this issue")

    urls = None
    if images is not None:
        if images:
            coros = [save_uploaded_image(f) for f in images]
            results = await asyncio.gather(*coros, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {r}")
            urls = [str(r) for r in results]

    payload = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if urls is not None:
        payload["images"] = urls

    updated = await svc_update_issue(db, issue_id, payload)
    return IssueResponse.model_validate(updated).model_dump()


@router.post("/{issue_id}/chat", status_code=status.HTTP_201_CREATED)
async def post_chat(issue_id: int, message: str = Form(...), db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_get_issue(db, issue_id)
    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to post chat to this issue")
    chat = await svc_add_chat(db, issue_id, current_user.user_id, message)
    return {"chat_id": chat.chat_id, "issue_id": chat.issue_id, "sender_id": chat.sender_id, "message": chat.message, "sent_at": chat.sent_at}


@router.get("/{issue_id}/chat")
async def list_chats(issue_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_get_issue(db, issue_id)
    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to view chats for this issue")
    items = await svc_list_chats(db, issue_id)
    return [{"chat_id": i.chat_id, "issue_id": i.issue_id, "sender_id": i.sender_id, "message": i.message, "sent_at": i.sent_at} for i in items]
