from fastapi import (
    APIRouter, Depends, UploadFile, File, Form, status, HTTPException, Query
)
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.database.postgres_connection import get_db
from app.dependencies.authentication import (
    get_current_user,
    get_user_permissions
)
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.issue_service.issues_service import (
    create_issue as svc_create_issue,
    list_issues as svc_list_issues,
    get_issue as svc_get_issue,
    update_issue as svc_update_issue,
    add_chat as svc_add_chat,
    list_chats as svc_list_chats,
)
from app.schemas.pydantic_models.issues import IssueResponse
from app.core.exceptions import ForbiddenError
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/api/issues", tags=["ISSUES"])


def _require_issue_write(user_permissions: dict):
    return (
        Resources.ISSUE_RESOLUTION.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ISSUE_RESOLUTION.value]
    )

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
    urls: List[str] = []
    user_id=current_user.user_id
    if images:
        coros = [save_uploaded_image(f) for f in images]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {r}")
        urls = [str(r) for r in results]

    payload = {
        "booking_id": booking_id,
        "room_id": room_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "images": urls,
    }

    obj = await svc_create_issue(db, payload)

    # audit issue create
    try:
        new_val = IssueResponse.model_validate(obj,from_attributes=True).model_dump()
        entity_id = f"issue:{getattr(obj, 'issue_id', None)}"
        await log_audit(entity="issue", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return IssueResponse.model_validate(obj,from_attributes=True).model_dump()


@router.get("/", response_model=Union[IssueResponse, List[IssueResponse]])
async def issues(
    issue_id: Optional[int] = Query(None, description="If provided, returns the single issue."),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Unified issues endpoint.

    - If `issue_id` is provided: returns that issue. Admins (issue-write) may fetch any issue;
      non-admins can fetch only their own.
    - If `issue_id` is not provided: admins get all issues; non-admins get only their own issues (paged).
    """
    is_admin = _require_issue_write(user_permissions)

    if issue_id is not None:
        obj = await svc_get_issue(db, issue_id)
        if not is_admin and obj.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to view this issue")
        return IssueResponse.model_validate(obj).model_dump()

    # list
    if is_admin:
        items = await svc_list_issues(db, limit=limit, offset=offset)
    else:
        items = await svc_list_issues(db, user_id=current_user.user_id, limit=limit, offset=offset)

    result = [IssueResponse.model_validate(i).model_dump() for i in items]
    return result

@router.get("/{issue_id}/chat")
async def get_chats(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Return chats for an issue.

    Allowed for admins (issue-write) or the owning user.
    """
    obj = await svc_get_issue(db, issue_id)

    is_admin = _require_issue_write(user_permissions)


    if not is_admin and obj.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to view chats for this issue")

    items = await svc_list_chats(db, issue_id)
    return [
        {
            "chat_id": i.chat_id,
            "issue_id": i.issue_id,
            "sender_id": i.sender_id,
            "message": i.message,
            "sent_at": i.sent_at,
        }
        for i in items
    ]


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: int,
    status: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Unified update: admins can update status; owners can update title/description/images.

    - If `status` is provided, requester must have ISSUE_RESOLUTION WRITE permission.
    - Only the issue owner may update title/description/images.
    """
    obj = await svc_get_issue(db, issue_id)

    is_admin = _require_issue_write(user_permissions)

    is_owner = obj.user_id == current_user.user_id

    if not is_admin and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to edit this issue")

    payload = {}

    # Admin-only: status
    if status is not None:
        if not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to change status")
        payload["status"] = status
        if str(status).upper() == "RESOLVED":
            payload["resolved_by"] = current_user.user_id

    # Owner-only: title/description/images
    if title is not None or description is not None or images is not None:
        if not is_owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the issue owner can modify title/description/images")

    urls = None
    if images is not None:
        if images:
            coros = [save_uploaded_image(f) for f in images]
            results = await asyncio.gather(*coros, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {r}")
            urls = [str(r) for r in results]
        else:
            urls = []

    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if urls is not None:
        payload["images"] = urls

    updated = await svc_update_issue(db, issue_id, payload)
    # audit issue update
    try:
        new_val = IssueResponse.model_validate(updated).model_dump()
        entity_id = f"issue:{getattr(updated, 'issue_id', None)}"
        await log_audit(entity="issue", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return IssueResponse.model_validate(updated).model_dump()


@router.post("/{issue_id}/chat", status_code=status.HTTP_201_CREATED)
async def post_chat(
    issue_id: int,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    obj = await svc_get_issue(db, issue_id)

    is_admin = _require_issue_write(user_permissions)

    if not is_admin and obj.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to post chat to this issue")

    chat = await svc_add_chat(db, issue_id, current_user.user_id, message)

    # audit chat message create
    try:
        entity_id = f"issue:{issue_id}:chat:{getattr(chat, 'chat_id', None)}"
        await log_audit(entity="issue_chat", entity_id=entity_id, action="INSERT", new_value={"message": chat.message}, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return {
        "chat_id": chat.chat_id,
        "issue_id": chat.issue_id,
        "sender_id": chat.sender_id,
        "message": chat.message,
        "sent_at": chat.sent_at,
    }