from fastapi import APIRouter, Depends, status, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import (
    AmenityCreate,
    AmenityResponse,
    Amenity,
    Room,
    RoomAmenityMapCreate,
    RoomAmenityMapResponse,
)
from app.dependencies.authentication import get_user_permissions, get_current_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.room_service.amenities_service import (
    create_amenity as svc_create_amenity,
    list_amenities as svc_list_amenities,
    get_amenity as svc_get_amenity,
    delete_amenity as svc_delete_amenity,
)
from app.services.room_service.room_amenities_service import (
    map_amenity as svc_map_amenity,
    get_rooms_for_amenity as svc_get_rooms_for_amenity,
    get_amenities_for_room as svc_get_amenities_for_room,
    unmap_amenity as svc_unmap_amenity,
)
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/amenities", tags=["AMENITIES"])


# ------------------- AMENITY CRUD -------------------

@router.post("/", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(
    payload: AmenityCreate,
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to create amenities")

    obj = await svc_create_amenity(db, payload)
    try:
        new_val = AmenityResponse.model_validate(obj).model_dump()
        entity_id = f"amenity:{getattr(obj, 'amenity_id', None)}"
        await log_audit(entity="amenity", entity_id=entity_id, action="INSERT", new_value=new_val)
    except Exception:
        pass

    return AmenityResponse.model_validate(obj).model_copy(update={"message": "Amenity created"})


@router.get("/")
async def get_amenities(
    amenity_id: Optional[int] = Query(None, description="If provided, return this amenity and its linked rooms"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if amenity_id is not None:
        amen = await svc_get_amenity(db, amenity_id)
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        return {
            "amenity": Amenity.model_validate(amen).model_dump(),
            "rooms": [Room.model_validate(r).model_dump() for r in rooms],
        }

    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


@router.delete("/{amenity_id}")
async def delete_amenity(
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete amenities")

    await svc_delete_amenity(db, amenity_id)
    return {"message": "Amenity deleted"}


# ------------------- ROOM-AMENITY MAPPING -------------------

@router.post("/map", response_model=RoomAmenityMapResponse, status_code=status.HTTP_201_CREATED)
async def map_amenity(
    payload: RoomAmenityMapCreate,
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to map amenities")

    obj = await svc_map_amenity(db, payload)
    try:
        entity_id = f"room:{obj.room_id}:amenity:{obj.amenity_id}"
        await log_audit(entity="room_amenity", entity_id=entity_id, action="INSERT", new_value=obj.__dict__)
    except Exception:
        pass

    return RoomAmenityMapResponse.model_validate(obj).model_copy(update={"message": "Mapped successfully"})


@router.get("/room/{room_id}")
async def get_amenities_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc_get_amenities_for_room(db, room_id)
    return {
        "room_id": room_id,
        "amenities": [
            {"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in items
        ],
    }


@router.delete("/unmap")
async def unmap_amenity(
    room_id: int,
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    user_permissions: dict = Depends(get_user_permissions),
):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to unmap amenities")

    await svc_unmap_amenity(db, room_id, amenity_id)
    return {"message": "Unmapped successfully"}
