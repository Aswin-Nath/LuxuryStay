from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.rooms import Rooms
from app.models.pydantic_models.room import RoomCreate, RoomResponse, Room
from fastapi import Depends
from app.dependencies.authentication import ensure_not_basic_user
from app.services.room_management.rooms_service import (
    create_room as svc_create_room,
    list_rooms as svc_list_rooms,
    get_room as svc_get_room,
    update_room as svc_update_room,
    change_room_status as svc_change_room_status,
    delete_room as svc_delete_room,
)

router = APIRouter(prefix="/api/rooms", tags=["ROOMS"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    obj = await svc_create_room(db, payload)
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Room created"})


@router.get("/", response_model=List[Room])
async def list_rooms(
    room_type_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    is_freezed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items = await svc_list_rooms(db, room_type_id=room_type_id, status_filter=status_filter, is_freezed=is_freezed)
    return [Room.model_validate(r) for r in items]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    obj = await svc_get_room(db, room_id)
    return RoomResponse.model_validate(obj)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, payload: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    obj = await svc_update_room(db, room_id, payload)
    return RoomResponse.model_validate(obj).model_copy(update={"message": "Updated successfully"})


@router.patch("/{room_id}/status")
async def change_room_status(room_id: int, status: str, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    await svc_change_room_status(db, room_id, status)
    return {"message": "Status updated"}


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(ensure_not_basic_user)):
    await svc_delete_room(db, room_id)
    return {"message": "Room deleted"}
