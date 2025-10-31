from fastapi import APIRouter, Depends, Form, status, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.issues_service import get_issue as svc_get_issue, list_issues as svc_list_issues, update_issue as svc_update_issue, add_chat as svc_add_chat, list_chats as svc_list_chats
from app.models.pydantic_models.issues import IssueResponse


router = APIRouter(prefix="/api/admin/issues", tags=["ISSUES_ADMIN"])


def _require_issue_write(user_permissions: dict):
    if not (
        Resources.ISSUE_RESOLUTION.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ISSUE_RESOLUTION.value]
    ):
        raise ForbiddenError("Insufficient permissions to manage issues")


@router.get("/", response_model=List[IssueResponse])
async def list_issues(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    _require_issue_write(user_permissions)
    items = await svc_list_issues(db, limit=limit, offset=offset)
    return [IssueResponse.model_validate(i).model_dump() for i in items]


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    _require_issue_write(user_permissions)
    obj = await svc_get_issue(db, issue_id)
    return IssueResponse.model_validate(obj).model_dump()


@router.put("/{issue_id}", response_model=IssueResponse)
async def admin_update_issue(
    issue_id: int,
    status: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
    current_user: Users = Depends(get_current_user),
):
    _require_issue_write(user_permissions)

    payload = {}
    if status is not None:
        payload["status"] = status
        # if admin marks resolved, set resolved_by to admin's user id
        if str(status).upper() == "RESOLVED":
            payload["resolved_by"] = current_user.user_id

    updated = await svc_update_issue(db, issue_id, payload)
    return IssueResponse.model_validate(updated).model_dump()


@router.post("/{issue_id}/chat", status_code=status.HTTP_201_CREATED)
async def admin_post_chat(issue_id: int, message: str = Form(...), db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions), current_user: Users = Depends(get_current_user)):
    _require_issue_write(user_permissions)
    chat = await svc_add_chat(db, issue_id, current_user.user_id, message)
    return {"chat_id": chat.chat_id, "issue_id": chat.issue_id, "sender_id": chat.sender_id, "message": chat.message, "sent_at": chat.sent_at}


@router.get("/{issue_id}/chat")
async def admin_list_chats(issue_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    _require_issue_write(user_permissions)
    items = await svc_list_chats(db, issue_id)
    return [{"chat_id": i.chat_id, "issue_id": i.issue_id, "sender_id": i.sender_id, "message": i.message, "sent_at": i.sent_at} for i in items]
