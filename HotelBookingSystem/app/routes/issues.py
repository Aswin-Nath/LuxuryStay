from fastapi import (
    APIRouter, Depends, UploadFile, File, Form, status, HTTPException, Query, Security
)
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.database.postgres_connection import get_db
from app.dependencies.authentication import (
    get_current_user,
    check_permission
)
from app.models.sqlalchemy_schemas.users import Users
from app.services.image_upload_service import save_uploaded_image
from app.services.issues_service import (
    create_issue as svc_create_issue,
    list_issues as svc_list_issues,
    get_issue as svc_get_issue,
    update_issue as svc_update_issue,
    add_chat as svc_add_chat,
    list_chats as svc_list_chats,
)
from app.schemas.pydantic_models.issues import IssueResponse, IssueCreate
from app.schemas.pydantic_models.images import ImageResponse
from app.utils.images_util import create_image
from app.core.cache import invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit


router = APIRouter(prefix="/issues", tags=["ISSUES"])


# ============================================================================
# 🔹 CREATE - Submit a new issue/complaint
# ============================================================================
@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    issue: IssueCreate = Depends(IssueCreate.as_form),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    """
    Submit a new customer issue or complaint.
    
    Creates an issue for reporting problems, complaints, or support requests. Issues are assigned
    unique IDs and tracked through resolution workflow. New issues start in OPEN status. Images
    can be attached via separate endpoint. Each issue belongs to the creating user.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        issue (IssueCreate): Form data containing title, description, and issue type.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user creating the issue.
    
    Returns:
        IssueResponse: Created issue with issue_id, status OPEN, timestamps, and creator info.
    
    Raises:
        HTTPException (400): If required fields missing or invalid.
    
    Side Effects:
        - Creates issue record with OPEN status.
        - Creates audit log entry.
        - Images uploaded separately via POST /issues/{issue_id}/images.
    """
    user_id = current_user.user_id

    payload = issue.model_dump()
    payload["user_id"] = user_id

    issue_record = await svc_create_issue(db, payload)

    # audit issue create
    try:
        new_val = IssueResponse.model_validate(issue_record, from_attributes=True).model_dump()
        entity_id = f"issue:{getattr(issue_record, 'issue_id', None)}"
        await log_audit(entity="issue", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return IssueResponse.model_validate(issue_record, from_attributes=True).model_dump()


# ============================================================================
# 🔹 CREATE - Upload images for an issue
# ============================================================================
@router.post("/{issue_id}/images", response_model=List[ImageResponse], status_code=status.HTTP_201_CREATED)
async def add_issue_images(
    issue_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    """
    Upload images to an issue/complaint.
    
    Allows issue creators to attach supporting images/screenshots. Multiple files supported.
    Images are stored via external provider. Only issue owner can upload images to their issues.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        issue_id (int): The issue to attach images to (must own).
        files (List[UploadFile]): Image files to upload.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (issue owner).
    
    Returns:
        List[ImageResponse]: Created image records with URLs.
    
    Raises:
        HTTPException (403): If user doesn't own the issue.
        HTTPException (404): If issue_id not found.
    
    Side Effects:
        - Uploads files to external storage.
        - Creates image records linked to issue.
        - Invalidates issue cache.
        - Creates audit log entry per image.
    """
    issue_record = await svc_get_issue(db, issue_id)
    if issue_record.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to upload images for this issue")

    images = []
    for file in files:
        url = await save_uploaded_image(file)
        image_record = await create_image(db, entity_type="issue", entity_id=issue_id, image_url=url, caption=None, uploaded_by=current_user.user_id)
        images.append(image_record)
        # audit each image created
        try:
            new_val = ImageResponse.model_validate(image_record).model_dump()
            entity_id = f"issue:{issue_id}:image:{getattr(image_record, 'image_id', None)}"
            await log_audit(entity="issue_image", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
        except Exception:
            pass

    # invalidate caches for this issue (if any)
    try:
        await invalidate_pattern(f"issues:*{issue_id}*")
    except Exception:
        pass

    return [ImageResponse.model_validate(i) for i in images]


# ============================================================================
# 🔹 READ - List all issues (ADMIN only - light response)
# ============================================================================
@router.get("/admin/", response_model=List[IssueResponse])
async def list_issues_admin(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    """
    Fetch paginated list of all issues (ADMIN only - light response for tables).
    
    Admin users can list all issues in the system. Returns lightweight response for table display.
    Use GET /issues/admin/{issue_id} for detailed view with full data.
    
    **Authorization:** Requires BOOKING:READ permission AND ADMIN role.
    
    Args:
        limit (int): Page size for list (default 50, max 100).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        token_payload (dict): Security token payload validating BOOKING:READ and ADMIN.
    
    Returns:
        List[IssueResponse]: List of all issue objects (light response).
    
    Examples:
        GET /issues/admin/ → All issues
        GET /issues/admin/?limit=100 → First 100 issues
    """
    items = await svc_list_issues(db, limit=limit, offset=offset)
    result = [IssueResponse.model_validate(i).model_dump() for i in items]
    return result


# ============================================================================
# 🔹 READ - Get single issue (ADMIN - detail view)
# ============================================================================
@router.get("/admin/{issue_id}", response_model=IssueResponse)
async def get_issue_admin(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    """
    Fetch single issue with full details (ADMIN only - detail view).
    
    Admin users can fetch any issue with all details. Returns complete issue data.
    Use GET /issues/admin/ for list view.
    
    **Authorization:** Requires BOOKING:READ permission AND ADMIN role.
    
    Args:
        issue_id (int): The issue ID to fetch (path parameter).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        token_payload (dict): Security token payload validating BOOKING:READ and ADMIN.
    
    Returns:
        IssueResponse: Complete issue object with all details.
    
    Raises:
        HTTPException (404): If issue_id not found.
    
    Examples:
        GET /issues/admin/5 → Full details of issue #5
    """
    issue_record = await svc_get_issue(db, issue_id)
    return IssueResponse.model_validate(issue_record).model_dump()


# ============================================================================
# 🔹 READ - List customer's own issues (CUSTOMER only - light response)
# ============================================================================
@router.get("/customer/", response_model=List[IssueResponse])
async def list_issues_customer(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Fetch paginated list of customer's own issues (CUSTOMER only - light response for tables).
    
    Customer users can only list their own issues. Returns lightweight response for table display.
    Use GET /issues/customer/{issue_id} for detailed view with full data.
    
    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role.
    
    Args:
        limit (int): Page size for list (default 50, max 100).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated customer user.
        token_payload (dict): Security token payload validating BOOKING:READ and CUSTOMER.
    
    Returns:
        List[IssueResponse]: List of customer's issues (light response).
    
    Examples:
        GET /issues/customer/ → All my issues
        GET /issues/customer/?limit=20 → First 20 of my issues
    """
    items = await svc_list_issues(db, user_id=current_user.user_id, limit=limit, offset=offset)
    result = [IssueResponse.model_validate(i).model_dump() for i in items]
    return result


# ============================================================================
# 🔹 READ - Get single issue (CUSTOMER - detail view, own issues only)
# ============================================================================
@router.get("/customer/{issue_id}", response_model=IssueResponse)
async def get_issue_customer(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Fetch single issue with full details (CUSTOMER only - own issues only, detail view).
    
    Customer users can only fetch their own issues with all details. Returns complete issue data.
    Use GET /issues/customer/ for list view of own issues.
    
    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role. User must own the issue.
    
    Args:
        issue_id (int): The issue ID to fetch (path parameter, must own).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated customer user.
        token_payload (dict): Security token payload validating BOOKING:READ and CUSTOMER.
    
    Returns:
        IssueResponse: Complete issue object with all details.
    
    Raises:
        HTTPException (403): If user doesn't own the issue.
        HTTPException (404): If issue_id not found.
    
    Examples:
        GET /issues/customer/3 → Full details of my issue #3
    """
    issue_record = await svc_get_issue(db, issue_id)
    if issue_record.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return IssueResponse.model_validate(issue_record).model_dump()

# ============================================================================
# 🔹 READ - Fetch all chat messages for an issue (ADMIN)
# ============================================================================
@router.get("/admin/{issue_id}/chat")
async def get_chats_admin(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    """
    Fetch all chat messages posted on an issue thread (ADMIN only).
    
    Admin users can view chat history for any issue.
    
    **Authorization:** Requires BOOKING:READ permission AND ADMIN role.
    
    Args:
        issue_id (int): The issue to fetch chats for.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        token_payload (dict): Security token payload validating BOOKING:READ and ADMIN.
    
    Returns:
        List[dict]: List of chat message dicts with keys: chat_id, issue_id, sender_id, message, sent_at.
    
    Raises:
        HTTPException (404): If issue_id not found in database.
    
    Side Effects:
        - Queries issue record and all associated chat messages.
    """
    issue_record = await svc_get_issue(db, issue_id)

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


# ============================================================================
# 🔹 READ - Fetch all chat messages for an issue (CUSTOMER)
# ============================================================================
@router.get("/customer/{issue_id}/chat")
async def get_chats_customer(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    """
    Fetch all chat messages posted on own issue thread (CUSTOMER only).
    
    Customer users can only view chat history on their own issues.
    
    **Authorization:** Requires BOOKING:READ permission AND CUSTOMER role.
    
    Args:
        issue_id (int): The customer's issue to fetch chats for.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated customer user (must be issue owner).
        token_payload (dict): Security token payload validating BOOKING:READ and CUSTOMER.
    
    Returns:
        List[dict]: List of chat message dicts with keys: chat_id, issue_id, sender_id, message, sent_at.
    
    Raises:
        HTTPException (403): If current_user is not the issue owner.
        HTTPException (404): If issue_id not found in database.
    
    Side Effects:
        - Queries issue record and all associated chat messages.
        - Access control enforced (ownership check).
    """
    issue_record = await svc_get_issue(db, issue_id)

    if issue_record.user_id != current_user.user_id:
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


# ============================================================================
# 🔹 UPDATE - Modify issue status/details
# ============================================================================
@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: int,
    status: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "ADMIN"]),
):
    """
    Update issue details with granular permission control.
    
    Supports two types of updates with different permission requirements:
    - Status updates (OPEN → IN_PROGRESS → RESOLVED → CLOSED): Admin only (ADMIN role).
      Auto-sets resolved_by to current_user when status set to RESOLVED.
    - Title/Description updates: Issue owner only. Used to clarify/add details to complaint.
    
    Enforces role-based authorization: non-owners cannot change title/description;
    CUSTOMER users cannot change status (ADMIN only).
    
    **Authorization:** Requires BOOKING:WRITE permission AND ADMIN role.
    
    Args:
        issue_id (int): The issue to update.
        status (Optional[str]): New issue status (e.g., "RESOLVED"). Admin-only.
        title (Optional[str]): New issue title. Owner-only.
        description (Optional[str]): New issue description. Owner-only.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (must be owner or admin depending on field).
        token_payload (dict): Security token payload validating ISSUE_RESOLUTION:WRITE permission.
    
    Returns:
        IssueResponse: Updated issue record.
    
    Raises:
        HTTPException (403): If non-admin tries to update status, or non-owner tries to update title/description.
        HTTPException (404): If issue_id not found.
    
    Side Effects:
        - Updates issue record in database.
        - Audit log entry created for UPDATE action with user_id and changed_by_user_id.
        - When status → RESOLVED, sets resolved_by to current_user.user_id.
    """
    issue_record = await svc_get_issue(db, issue_id)

    is_admin = True  # User has ISSUE_RESOLUTION:WRITE via Security

    is_owner = issue_record.user_id == current_user.user_id

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
    # Owner-only: title/description
    if title!="" or description!="":
        if not is_owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the issue owner can modify title/description/images")



    if title!="":
        payload["title"] = title
    if description!="":
        payload["description"] = description

    updated = await svc_update_issue(db, issue_id, payload)
    # audit issue update
    try:
        new_val = IssueResponse.model_validate(updated).model_dump()
        entity_id = f"issue:{getattr(updated, 'issue_id', None)}"
        await log_audit(entity="issue", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return IssueResponse.model_validate(updated).model_dump()


# ============================================================================
# 🔹 CREATE - Customer post a chat message on their issue thread
# ============================================================================
@router.post("/customer/{issue_id}/chat", status_code=status.HTTP_201_CREATED)
async def post_customer_chat(
    issue_id: int,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    """
    Post a chat message to an issue resolution thread (customer only).
    
    Allows customers to add messages to their own issue conversation. Only the issue creator
    can use this endpoint. Used for providing updates, answering support questions, and
    communication with support team.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role. Users can only chat on their own issues.
    
    Args:
        issue_id (int): The issue to post message to (must own).
        message (str): The chat message text (required, non-empty).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (must be issue owner).
    
    Returns:
        dict: Created chat message with keys: chat_id, issue_id, sender_id, message, sent_at.
    
    Raises:
        HTTPException (403): If current_user is not the issue owner.
        HTTPException (404): If issue_id not found.
    
    Side Effects:
        - Inserts new chat_message record linked to issue.
        - Sends notification to support team if applicable.
        - Audit log entry created with action=INSERT.
    """
    if not message or not message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")
    
    issue_record = await svc_get_issue(db, issue_id)
    if not issue_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    # Verify ownership - customer can only chat on their own issues
    if issue_record.user_id != current_user.user_id:
        raise ForbiddenException("You can only chat on your own issues")

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


# ============================================================================
# 🔹 CREATE - Admin post a chat message on any issue thread
# ============================================================================
@router.post("/admin/{issue_id}/chat", status_code=status.HTTP_201_CREATED)
async def post_admin_chat(
    issue_id: int,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "ADMIN"]),
):
    """
    Post a chat message to an issue resolution thread (admin only).
    
    Allows admin/support staff to add messages to any issue conversation. Admins can respond
    to customer issues, provide updates, and coordinate issue resolution. Used for support
    team communication on issue threads.
    
    **Authorization:** Requires BOOKING:WRITE permission AND ADMIN role.
    
    Args:
        issue_id (int): The issue to post message to (any issue allowed).
        message (str): The chat message text (required, non-empty).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        token_payload (dict): Security token payload validating ISSUE_RESOLUTION:WRITE permission.
    
    Returns:
        dict: Created chat message with keys: chat_id, issue_id, sender_id, message, sent_at.
    
    Raises:
        HTTPException (403): If user lacks ISSUE_RESOLUTION:WRITE permission.
        HTTPException (404): If issue_id not found.
    
    Side Effects:
        - Inserts new chat_message record linked to issue.
        - Sends notification to issue creator.
        - Audit log entry created with action=INSERT.
    """
    if not message or not message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")
    
    issue_record = await svc_get_issue(db, issue_id)
    if not issue_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

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