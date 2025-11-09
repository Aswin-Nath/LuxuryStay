from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.offers import OfferCreate, OfferResponse
from app.services.offer_service.offers_service import create_offer as svc_create_offer, get_offer as svc_get_offer, list_offers as svc_list_offers
from app.services.offer_service.offers_service import update_offer as svc_update_offer, soft_delete_offer as svc_soft_delete_offer
from app.dependencies.authentication import get_user_permissions, get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/offers", tags=["OFFERS"])




# ============================================================================
# 🔹 CREATE - Create a new offer with room mappings
# ============================================================================
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
    offer_record = await svc_create_offer(db, payload, created_by=current_user.user_id)
    # invalidate offer list caches
    await invalidate_pattern("offers:*")
    # audit offer create
    try:
        new_val = OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})
        entity_id = f"offer:{getattr(offer_record, 'offer_id', None)}"
        await log_audit(entity="offer", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    # Use pydantic model_validate (from_attributes=True) to convert SQLAlchemy object
    # Exclude created_at from any API responses (handled internally by backend)
    return OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 READ - Fetch single offer by ID
# ============================================================================
@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    offer_record = await svc_get_offer(db, offer_id)
    # Exclude created_at from response
    return OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 READ - Fetch list of all offers (paginated)
# ============================================================================
@router.get("/", response_model=List[OfferResponse])
async def list_offers(limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    cache_key = f"offers:limit:{limit}:offset:{offset}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_offers(db, limit=limit, offset=offset)
    result = [OfferResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]
    await set_cached(cache_key, result, ttl=120)
    return result


# ============================================================================
# 🔹 UPDATE - Modify existing offer details
# ============================================================================
@router.put("/{offer_id}", response_model=OfferResponse)
async def edit_offer(offer_id: int, payload: OfferCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions), current_user: Users = Depends(get_current_user)):
    # Permission check: require OFFER_MANAGEMENT.WRITE
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to edit offers")

    offer_record = await svc_update_offer(db, offer_id, payload, updated_by=current_user.user_id)
    # invalidate offers cache on update
    await invalidate_pattern("offers:*")
    # audit offer update
    try:
        new_val = OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})
        entity_id = f"offer:{getattr(offer_record, 'offer_id', None)}"
        await log_audit(entity="offer", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 DELETE - Remove offer from system (soft delete)
# ============================================================================
@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer(offer_id: int, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions)):
    # Permission check: require OFFER_MANAGEMENT.WRITE
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete offers")

    await svc_soft_delete_offer(db, offer_id)
    await invalidate_pattern("offers:*")
    return {"message":"offer deleted"}
