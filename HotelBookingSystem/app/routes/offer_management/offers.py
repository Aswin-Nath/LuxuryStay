from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.offers import OfferCreate, OfferRoomMapBase, OfferResponse
from app.models.sqlalchemy_schemas.offers import OfferRoomMap
from app.services.offer_service.offers_service import create_offer as svc_create_offer, get_offer as svc_get_offer, list_offers as svc_list_offers
from app.services.offer_service.offers_service import update_offer as svc_update_offer, soft_delete_offer as svc_soft_delete_offer
from app.dependencies.authentication import get_user_permissions, get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from pydantic import Field
from decimal import Decimal


router = APIRouter(prefix="/api/offers", tags=["OFFERS"])




@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(payload: OfferCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions), current_user: Users = Depends(get_current_user)):
    """Create an offer and its room mappings via the service layer.

    Only users with Resources.OFFER_MANAGEMENT and PermissionTypes.WRITE may perform this action.
    """
    # Permission check: require OFFER_MANAGEMENT.WRITE (user_permissions keys are normalized to strings)
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to create offers")

    # Use current authenticated user as the creator — ignore any client-provided created_by value
    obj = await svc_create_offer(db, payload, created_by=current_user.user_id)
    # Use pydantic model_validate (from_attributes=True) to convert SQLAlchemy object
    # Exclude created_at from any API responses (handled internally by backend)
    return OfferResponse.model_validate(obj).model_dump(exclude={"created_at"})


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    obj = await svc_get_offer(db, offer_id)
    # Exclude created_at from response
    return OfferResponse.model_validate(obj).model_dump(exclude={"created_at"})


@router.get("/", response_model=List[OfferResponse])
async def list_offers(limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    items = await svc_list_offers(db, limit=limit, offset=offset)
    # Exclude created_at from list responses
    return [OfferResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


@router.put("/{offer_id}", response_model=OfferResponse)
async def edit_offer(offer_id: int, payload: OfferCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions), current_user: Users = Depends(get_current_user)):
    # Permission check: require OFFER_MANAGEMENT.WRITE
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to edit offers")

    obj = await svc_update_offer(db, offer_id, payload, updated_by=current_user.user_id)
    return OfferResponse.model_validate(obj).model_dump(exclude={"created_at"})


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer(offer_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Permission check: require OFFER_MANAGEMENT.WRITE
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete offers")

    await svc_soft_delete_offer(db, offer_id)
    return None
