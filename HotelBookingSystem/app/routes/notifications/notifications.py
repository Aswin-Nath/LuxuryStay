from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.models.pydantic_models.notifications import NotificationCreate, NotificationResponse
from app.services.notification_service.notifications_service import add_notification as svc_add, list_user_notifications as svc_list

router = APIRouter(prefix="/api/notifications", tags=["NOTIFICATIONS"])


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(payload: NotificationCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    # Allow creation by any authenticated service user. Ownership is by recipient_user_id in payload.
    obj = await svc_add(db, payload)
    return NotificationResponse.model_validate(obj).model_dump()


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
