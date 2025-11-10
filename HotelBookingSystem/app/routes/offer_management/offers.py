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
    """
    Create a new promotional offer.
    
    Creates a new offer applicable to specific rooms with a discount percentage and validity period.
    Offers automatically determine discount amounts based on room prices. Creator is set to current user.
    Multiple offers can be active simultaneously with system selecting best applicable offer at booking time.
    
    **Authorization:** Requires OFFER_MANAGEMENT:WRITE permission.
    
    Args:
        payload (OfferCreate): Offer details (name, description, discount_percentage, valid_from, valid_to, room_ids).
        db (AsyncSession): Database session dependency.
        user_permissions (dict): Current user's permissions.
        current_user (Users): Authenticated user creating the offer.
    
    Returns:
        OfferResponse: Created offer with offer_id, discount info, and timestamps (created_at excluded).
    
    Raises:
        HTTPException (403): If user lacks OFFER_MANAGEMENT:WRITE permission.
        HTTPException (404): If any specified room_id not found.
    
    Side Effects:
        - Invalidates offers cache pattern ("offers:*").
        - Creates audit log entry.
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
    """
    Retrieve a single offer by ID.
    
    Fetches offer details including discount percentage, validity period, and associated rooms.
    Useful for detailed offer information display and validation during booking process.
    
    Args:
        offer_id (int): The offer ID to retrieve.
        db (AsyncSession): Database session dependency.
    
    Returns:
        OfferResponse: Offer details with rooms and discount info (created_at excluded).
    
    Raises:
        HTTPException (404): If offer_id not found.
    """
    offer_record = await svc_get_offer(db, offer_id)
    # Exclude created_at from response
    return OfferResponse.model_validate(offer_record).model_dump(exclude={"created_at"})


# ============================================================================
# 🔹 READ - Fetch list of all offers (paginated)
# ============================================================================
@router.get("/", response_model=List[OfferResponse])
async def list_offers(limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    """
    Retrieve list of all active offers (paginated).
    
    Fetches all active offers with pagination support. Results are cached for 120 seconds to
    reduce database load. Useful for displaying available promotions to customers.
    
    Args:
        limit (int): Number of offers to return (default 20, max 200).
        offset (int): Pagination offset (default 0).
        db (AsyncSession): Database session dependency.
    
    Returns:
        List[OfferResponse]: List of offers with discount and room info (created_at excluded).
    
    Side Effects:
        - Uses Redis cache with TTL of 120 seconds (key: "offers:limit:{limit}:offset:{offset}").
    """
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
    """
    Update an existing offer.
    
    Modifies offer details like name, description, discount percentage, or validity period.
    Automatically recalculates discount amounts for affected rooms. Changes take effect immediately.
    
    **Authorization:** Requires OFFER_MANAGEMENT:WRITE permission.
    
    Args:
        offer_id (int): The offer ID to update.
        payload (OfferCreate): Updated offer details.
        db (AsyncSession): Database session dependency.
        user_permissions (dict): Current user's permissions.
        current_user (Users): Authenticated user.
    
    Returns:
        OfferResponse: Updated offer with new details and timestamps.
    
    Raises:
        HTTPException (403): If user lacks OFFER_MANAGEMENT:WRITE permission.
        HTTPException (404): If offer_id not found.
    
    Side Effects:
        - Invalidates offers cache pattern ("offers:*").
        - Creates audit log entry.
    """
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
    """
    Delete an offer (soft delete).
    
    Marks an offer as deleted. The offer record remains in the database for historical purposes
    but is excluded from normal queries. Active bookings are not affected, only future bookings won't
    apply this offer.
    
    **Authorization:** Requires OFFER_MANAGEMENT:WRITE permission.
    
    Args:
        offer_id (int): The offer ID to delete.
        db (AsyncSession): Database session dependency.
        user_permissions (dict): Current user's permissions.
    
    Returns:
        None (204 No Content)
    
    Raises:
        HTTPException (403): If user lacks OFFER_MANAGEMENT:WRITE permission.
        HTTPException (404): If offer_id not found.
    
    Side Effects:
        - Soft-deletes the offer record.
        - Invalidates offers cache pattern ("offers:*").
    """
    if not (
        Resources.OFFER_MANAGEMENT.value in user_permissions
        and PermissionTypes.WRITE.value in user_permissions[Resources.OFFER_MANAGEMENT.value]
    ):
        raise ForbiddenError("Insufficient permissions to delete offers")

    await svc_soft_delete_offer(db, offer_id)
    await invalidate_pattern("offers:*")
    return {"message":"offer deleted"}
