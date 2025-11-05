from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import AmenityCreate, AmenityResponse, Amenity, Room
from app.dependencies.authentication import get_user_permissions, get_current_user
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.room_service.amenities_service import (
    create_amenity as svc_create_amenity,
    list_amenities as svc_list_amenities,
    get_amenity as svc_get_amenity,
    delete_amenity as svc_delete_amenity,
)
from app.services.room_service.room_amenities_service import get_rooms_for_amenity as svc_get_rooms_for_amenity

router = APIRouter(prefix="/api/amenities", tags=["AMENITIES"])


@router.post("/", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(payload: AmenityCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # require WRITE on Room_Management
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to create amenities")
    obj = await svc_create_amenity(db, payload)
    return AmenityResponse.model_validate(obj).model_copy(update={"message": "Amenity created"})


@router.get("/")
async def get_amenities(
    amenity_id: Optional[int] = Query(None, description="If provided, return this amenity and its linked rooms"),
    db: AsyncSession = Depends(get_db),
    # require authentication for this endpoint (basic users allowed)
    _current_user = Depends(get_current_user),
):
    if amenity_id is not None:
        amen = await svc_get_amenity(db, amenity_id)
        # fetch linked rooms
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        return {
            "amenity": Amenity.model_validate(amen).model_dump(),
            "rooms": [Room.model_validate(r).model_dump() for r in rooms],
        }

    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


@router.delete("/{amenity_id}")
async def delete_amenity(amenity_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    if not (
        Resources.ROOM_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.ROOM_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete amenities")
    await svc_delete_amenity(db, amenity_id)
    return {"message": "Amenity deleted"}
