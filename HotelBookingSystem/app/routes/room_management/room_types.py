from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.rooms import RoomTypes
from app.models.pydantic_models.room import RoomTypeCreate, RoomTypeResponse
from fastapi import Depends
from app.dependencies.authentication import get_user_permissions
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.room_service.room_types_service import (
    create_room_type as svc_create_room_type,
    list_room_types as svc_list_room_types,
    get_room_type as svc_get_room_type,
    update_room_type as svc_update_room_type,
    soft_delete_room_type as svc_soft_delete_room_type,
)

router = APIRouter(prefix="/api/room-types", tags=["ROOM_TYPES"])


@router.post("/", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Permission check: require room_service.WRITE
    if not (
        Resources.room_service.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.room_service.value]
    ):
        raise ForbiddenError("Insufficient permissions to create room types")

    obj = await svc_create_room_type(db, payload)
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Room type created"})


@router.get("/", response_model=List[RoomTypeResponse])
async def list_room_types(include_deleted: Optional[bool] = Query(False), db: AsyncSession = Depends(get_db)):
    items = await svc_list_room_types(db, include_deleted=include_deleted)
    return [RoomTypeResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in items]


@router.get("/{room_type_id}", response_model=RoomTypeResponse)
async def get_room_type(room_type_id: int, db: AsyncSession = Depends(get_db)):
    obj = await svc_get_room_type(db, room_type_id)
    return RoomTypeResponse.model_validate(obj)


@router.put("/{room_type_id}", response_model=RoomTypeResponse)
async def update_room_type(room_type_id: int, payload: RoomTypeCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    if not (
        Resources.room_service.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.room_service.value]
    ):
        raise ForbiddenError("Insufficient permissions to update room types")

    obj = await svc_update_room_type(db, room_type_id, payload)
    return RoomTypeResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.delete("/{room_type_id}")
async def soft_delete_room_type(room_type_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    if not (
        Resources.room_service.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.room_service.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete room types")

    await svc_soft_delete_room_type(db, room_type_id)
    return {"message": "Room type soft-deleted"}
