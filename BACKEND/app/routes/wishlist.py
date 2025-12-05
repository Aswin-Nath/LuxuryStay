from fastapi import APIRouter, Depends, status,Security
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.wishlist import WishlistCreate, WishlistResponse, WishlistRoomResponse, WishlistOfferResponse, WishlistToggle
from app.services.wishlist_service import add_to_wishlist as svc_add, list_user_wishlist as svc_list, remove_wishlist as svc_remove, list_user_wishlist_rooms as svc_list_rooms, list_user_wishlist_offers as svc_list_offers, toggle_wishlist as svc_toggle
from app.dependencies.authentication import get_current_user,check_permission
from app.models.sqlalchemy_schemas.users import Users
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_util import log_audit
from app.crud.wishlist import get_wishlist_by_user_and_item


router = APIRouter(prefix="/wishlist", tags=["WISHLIST"])


# ============================================================================
# 🔹 CREATE - Add room to user's wishlist
# ============================================================================
@router.post("/", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def add_wishlist(
    payload: WishlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])
):
    """
    Add a room or offer to user's wishlist.
    
    Allows customers to save rooms or offers for later consideration. Each user can wishlist
    multiple items. Duplicate wishlists for same item are prevented. Supports:
    - room_type_id: Save specific room type
    - offer_id: Save specific offer
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        payload (WishlistCreate): Request with room_id to add.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (must be basic user/customer).
    
    Returns:
        WishlistResponse: Created wishlist entry with wishlist_id and timestamps.
    
    Raises:
        HTTPException (403): If user is not a basic user (admin/manager).
        HTTPException (404): If room_id not found.
    
    Side Effects:
        - Invalidates user's wishlist cache.
        - Creates audit log entry.
    """

    wishlist_record = await svc_add(db, payload, current_user)
    # audit wishlist create
    try:
        new_val = WishlistResponse.model_validate(wishlist_record).model_dump()
        entity_id = f"wishlist:{getattr(wishlist_record, 'wishlist_id', None)}"
        await log_audit(entity="wishlist", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return WishlistResponse.model_validate(wishlist_record).model_dump()


# ============================================================================
# 🔹 TOGGLE - Add or remove item from wishlist (unified endpoint)
# ============================================================================
@router.post("/toggle", response_model=dict, status_code=status.HTTP_200_OK)
async def toggle_wishlist(
    payload: WishlistToggle,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])
):
    """
    Toggle an item in user's wishlist (add if not present, remove if present).
    
    Unified endpoint that handles both adding and removing items from wishlist.
    - If item is NOT in wishlist: adds it and returns action='added' with wishlist_id
    - If item IS in wishlist: removes it and returns action='removed'
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        payload (WishlistToggle): Request with type ('room' or 'offer'), room_type_id or offer_id.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        dict: {"action": "added"/"removed", "wishlist_id": id (only if added)}
    
    Raises:
        HTTPException (400): If payload is invalid.
        HTTPException (403): If user lacks permission.
    """
    result = await svc_toggle(db, payload, current_user)
    
    # audit wishlist toggle
    try:
        action_text = "added to" if result.get("action") == "added" else "removed from"
        await log_audit(
            user_id=current_user.user_id,
            action=f"WISHLIST_{result.get('action').upper()}",
            resource_type="WISHLIST",
            resource_id=result.get("wishlist_id"),
            old_val=None,
            new_val=result
        )
    except Exception:
        pass  # Audit failure doesn't stop the operation
    
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return result



@router.get("/", response_model=List[WishlistResponse])
async def list_wishlist(db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user),    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])):
    """
    Retrieve authenticated user's complete wishlist (all items).
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (wishlist owner).
    
    Returns:
        List[WishlistResponse]: List of wishlisted items.
    
    Side Effects:
        - Uses Redis cache with TTL of 120 seconds (key: "wishlist:user:{user_id}").
    """
    cache_key = f"wishlist:user:{current_user.user_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list(db, current_user.user_id)
    response_list = [WishlistResponse.model_validate(i).model_dump() for i in items]
    await set_cached(cache_key, response_list, ttl=120)
    return response_list


# ============================================================================
# 🔹 READ - Fetch user's wishlist ROOMS with full details
# ============================================================================
@router.get("/rooms", response_model=List[dict])
async def list_wishlist_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])
):
    """
    Retrieve authenticated user's wishlist rooms with full details.
    
    Returns detailed information about each wishlisted room type including:
    - Room type name, price per night, description
    - Amenities list
    - Occupancy limits (adults/children)
    - Square footage
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        List[dict]: List of wishlisted rooms with full details.
    
    Side Effects:
        - Uses Redis cache with TTL of 120 seconds.
    """
    cache_key = f"wishlist:user:{current_user.user_id}:rooms"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    rooms_data = await svc_list_rooms(db, current_user.user_id)
    await set_cached(cache_key, rooms_data, ttl=120)
    return rooms_data


# ============================================================================
# 🔹 READ - Fetch user's wishlist OFFERS with full details
# ============================================================================
@router.get("/offers", response_model=List[dict])
async def list_wishlist_offers(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])
):
    """
    Retrieve authenticated user's wishlist offers with full details.
    
    Returns detailed information about each wishlisted offer including:
    - Offer name, description, discount percentage
    - Room types included in the offer
    - Valid from/to dates
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
    
    Returns:
        List[dict]: List of wishlisted offers with full details.
    
    Side Effects:
        - Uses Redis cache with TTL of 120 seconds.
    """
    cache_key = f"wishlist:user:{current_user.user_id}:offers"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    offers_data = await svc_list_offers(db, current_user.user_id)
    await set_cached(cache_key, offers_data, ttl=120)
    return offers_data




# ============================================================================
# 🔹 DELETE - Remove room from user's wishlist
# ============================================================================
@router.delete("/{wishlist_id}", status_code=status.HTTP_201_CREATED)
async def delete_wishlist(wishlist_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user),    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])):
    """
    Remove a room from user's wishlist.
    
    Removes a specific wishlisted item. Only the wishlist owner can remove their own items.
    Attempting to remove another user's wishlist item returns 403.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        wishlist_id (int): The wishlist entry ID to remove.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (must own wishlist entry).
    
    Returns:
        dict: Confirmation message for successful deletion.
    
    Raises:
        HTTPException (403): If user doesn't own the wishlist entry.
        HTTPException (404): If wishlist_id not found.
    
    Side Effects:
        - Deletes wishlist entry from database.
        - Invalidates user's wishlist cache pattern.
    """
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return await svc_remove(db, wishlist_id, current_user.user_id)


# ============================================================================
# 🔹 CHECK - Verify if item is in wishlist
# ============================================================================
@router.get("/check", response_model=dict)
async def check_wishlist(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    room_type_id: int = None,
    offer_id: int = None
):
    """
    Check if a specific room or offer is in user's wishlist.
    
    Returns boolean indicating if the item exists in the user's wishlist.
    """
    if not room_type_id and not offer_id:
        return {"in_wishlist": False}
    
    cache_key = f"wishlist:user:{current_user.user_id}:check:{room_type_id or offer_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return {"in_wishlist": cached}

    existing = await get_wishlist_by_user_and_item(db, current_user.user_id, room_type_id, offer_id)
    in_wishlist = existing is not None
    
    await set_cached(cache_key, in_wishlist, ttl=60)
    return {"in_wishlist": in_wishlist}
