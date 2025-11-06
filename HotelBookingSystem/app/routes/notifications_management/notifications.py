from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.schemas.pydantic_models.notifications import NotificationCreate, NotificationResponse
from app.services.notification_service.notifications_service import add_notification as svc_add, list_user_notifications as svc_list, mark_notification_as_read as svc_mark_read
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/api/notifications", tags=["NOTIFICATIONS"])



@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    include_read: bool = True,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    items = await svc_list(db, current_user.user_id, include_read=include_read, include_deleted=include_deleted, limit=limit, offset=offset)
    return [NotificationResponse.model_validate(i).model_dump() for i in items]


@router.put("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Mark the authenticated user's notification as read."""
    await svc_mark_read(db, notification_id, current_user.user_id)
    # audit mark read
    try:
        entity_id = f"notification:{notification_id}"
        await log_audit(entity="notification", entity_id=entity_id, action="UPDATE", new_value={"read": True}, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return {"notification_id": notification_id, "message": "Marked as read"}
