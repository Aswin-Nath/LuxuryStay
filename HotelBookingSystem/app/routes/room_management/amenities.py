from fastapi import APIRouter, Depends, status, Query, Security
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.room import (
    AmenityCreate,
    AmenityResponse,
    Amenity,
    Room,
    RoomAmenityMapCreate,
    RoomAmenityMapResponse,
)
from app.dependencies.authentication import check_permission, get_current_user
from app.core.exceptions import ForbiddenException
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
    map_amenities_bulk as svc_map_amenities_bulk,
    unmap_amenities_bulk as svc_unmap_amenities_bulk,
)
from app.utils.audit_util import log_audit


# ===============================================
# HELPER MODELS FOR FLEXIBLE INPUT
# ===============================================
class RoomAmenityMapFlexible(BaseModel):
    """Model for mapping list of amenities to a room"""
    room_id: int
    amenity_ids: List[int]


router = APIRouter(prefix="/amenities", tags=["AMENITIES"])


# ------------------- AMENITY CRUD -------------------

# ============================================================================
# 🔹 CREATE - Add a new amenity to the system
# ============================================================================
@router.post("/", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
async def create_amenity(
    payload: AmenityCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):

    amenity_record = await svc_create_amenity(db, payload)
    try:
        new_val = AmenityResponse.model_validate(amenity_record).model_dump()
        entity_id = f"amenity:{getattr(amenity_record, 'amenity_id', None)}"
        await log_audit(entity="amenity", entity_id=entity_id, action="INSERT", new_value=new_val)
    except Exception:
        pass

    return AmenityResponse.model_validate(amenity_record).model_copy(update={"message": "Amenity created"})


# ============================================================================
# 🔹 READ - Fetch amenity details (single or list)
# ============================================================================
@router.get("/")
async def get_amenities(
    amenity_id: Optional[int] = Query(None, description="If provided, return this amenity and its linked rooms"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if amenity_id is not None:
        amenity_record = await svc_get_amenity(db, amenity_id)
        rooms = await svc_get_rooms_for_amenity(db, amenity_id)
        return {
            "amenity": Amenity.model_validate(amenity_record).model_dump(),
            "rooms": [Room.model_validate(r).model_dump() for r in rooms],
        }

    items = await svc_list_amenities(db)
    return [Amenity.model_validate(a) for a in items]


# ------------------- ROOM-AMENITY MAPPING -------------------

# ============================================================================
# 🔹 MAP - Link amenities to a room
# ============================================================================
@router.post("/map", status_code=status.HTTP_201_CREATED)
async def map_amenity(
    payload: RoomAmenityMapFlexible,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """
    Map amenities to a room. Accepts a list of amenity IDs.
    
    Request:
    {
        "room_id": 1,
        "amenity_ids": [1, 2, 3, 4]
    }
    
    For single amenity, just provide a list with one item:
    {
        "room_id": 1,
        "amenity_ids": [5]
    }
    """

    amenity_ids = payload.amenity_ids

    # If only one amenity, use single mapping for simplicity
    if len(amenity_ids) == 1:
        amenity_id = amenity_ids[0]
        single_payload = RoomAmenityMapCreate(room_id=payload.room_id, amenity_id=amenity_id)
        amenity_mapping_record = await svc_map_amenity(db, single_payload)
        try:
            entity_id = f"room:{amenity_mapping_record.room_id}:amenity:{amenity_mapping_record.amenity_id}"
            await log_audit(entity="room_amenity", entity_id=entity_id, action="INSERT", new_value=amenity_mapping_record.__dict__)
        except Exception:
            pass
        return RoomAmenityMapResponse.model_validate(amenity_mapping_record).model_copy(update={"message": "Mapped successfully"})

    # Multiple amenities - use bulk mapping
    mapping_response = await svc_map_amenities_bulk(db, payload.room_id, amenity_ids)
    
    try:
        await log_audit(
            entity="room_amenity",
            entity_id=f"room:{payload.room_id}",
            action="INSERT",
            new_value={
                "room_id": payload.room_id,
                "amenity_ids": amenity_ids,
                "result_summary": {
                    "successfully_mapped": len(mapping_response["successfully_mapped"]),
                    "already_existed": len(mapping_response["already_existed"]),
                    "failed": len(mapping_response["failed"]),
                }
            }
        )
    except Exception:
        pass

    return {
        "room_id": mapping_response["room_id"],
        "successfully_mapped": mapping_response["successfully_mapped"],
        "already_existed": mapping_response["already_existed"],
        "failed": mapping_response["failed"],
        "message": f"Mapping completed: {len(mapping_response['successfully_mapped'])} mapped, {len(mapping_response['already_existed'])} already existed, {len(mapping_response['failed'])} failed"
    }


# ============================================================================
# 🔹 READ - Get all amenities for a specific room
# ============================================================================
@router.get("/room/{room_id}")
async def get_amenities_for_room(room_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc_get_amenities_for_room(db, room_id)
    return {
        "room_id": room_id,
        "amenities": [
            {"amenity_id": a.amenity_id, "amenity_name": a.amenity_name} for a in items
        ],
    }


# ============================================================================
# 🔹 DELETE - Unmap amenities from a room
# ============================================================================
@router.delete("/unmap")
async def unmap_amenity(
    payload: RoomAmenityMapFlexible,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    """
    Unmap amenities from a room. Accepts a list of amenity IDs.
    
    Single amenity:
    {
        "room_id": 1,
        "amenity_ids": [5]
    }
    
    Multiple amenities:
    {
        "room_id": 1,
        "amenity_ids": [1, 2, 3]
    }
    """

    amenity_ids = payload.amenity_ids

    # If only one amenity, use single unmapping for simplicity
    if len(amenity_ids) == 1:
        await svc_unmap_amenity(db, payload.room_id, amenity_ids[0])
        try:
            entity_id = f"room:{payload.room_id}:amenity:{amenity_ids[0]}"
            await log_audit(entity="room_amenity", entity_id=entity_id, action="DELETE")
        except Exception:
            pass
        return {"message": "Unmapped successfully"}

    # Multiple amenities - use bulk unmapping
    result = await svc_unmap_amenities_bulk(db, payload.room_id, amenity_ids)
    
    try:
        await log_audit(
            entity="room_amenity",
            entity_id=f"room:{payload.room_id}",
            action="DELETE",
            new_value={
                "room_id": payload.room_id,
                "amenity_ids": amenity_ids,
                "result_summary": {
                    "successfully_unmapped": len(result["successfully_unmapped"]),
                    "not_found": len(result["not_found"]),
                    "failed": len(result["failed"]),
                }
            }
        )
    except Exception:
        pass

    return {
        "room_id": result["room_id"],
        "successfully_unmapped": result["successfully_unmapped"],
        "not_found": result["not_found"],
        "failed": result["failed"],
        "message": f"Unmapping completed: {len(result['successfully_unmapped'])} unmapped, {len(result['not_found'])} not found, {len(result['failed'])} failed"
    }


# ============================================================================
# 🔹 DELETE - Remove amenity from system
# ============================================================================
@router.delete("/{amenity_id}")
async def delete_amenity(
    amenity_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ROOM_MANAGEMENT:WRITE"]),
):
    await svc_delete_amenity(db, amenity_id)
    return {"message": "Amenity deleted"}

