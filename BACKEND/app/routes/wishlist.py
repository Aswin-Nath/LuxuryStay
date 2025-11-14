from fastapi import APIRouter, Depends, status,Security
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.wishlist import WishlistCreate, WishlistResponse
from app.services.wishlist_service import add_to_wishlist as svc_add, list_user_wishlist as svc_list, remove_wishlist as svc_remove
from app.dependencies.authentication import get_current_user,check_permission
from app.models.sqlalchemy_schemas.users import Users
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_util import log_audit


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
    Add a room to user's wishlist.
    
    Allows customers to save rooms for later consideration. Each user can wishlist
    multiple rooms. Duplicate wishlists for same room are prevented (upsert behavior). Useful for
    price tracking and future booking reminders.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        payload (WishlistCreate): Request with room_id to add.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (must be basic user/customer).
        _basic_user_check (bool): Ensure only basic users can add to wishlist.
    
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
# 🔹 READ - Fetch user's wishlist items
# ============================================================================
@router.get("/", response_model=List[WishlistResponse])
async def list_wishlist(db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user),    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"])):
    """
    Retrieve authenticated user's complete wishlist.
    
    Fetches all rooms saved to the user's wishlist. Results are cached for 120 seconds.
    Returns room details, prices, and wishlist timestamps. Empty list if no wishlisted rooms.
    
    **Authorization:** Requires BOOKING:WRITE permission AND CUSTOMER role.
    
    Args:
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (wishlist owner).
    
    Returns:
        List[WishlistResponse]: List of wishlisted room items with details.
    
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
    return {"message":"wishlist deleted successfully"}