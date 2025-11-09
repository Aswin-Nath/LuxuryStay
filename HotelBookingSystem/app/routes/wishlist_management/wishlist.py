from fastapi import APIRouter, Depends, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.wishlist import WishlistCreate, WishlistResponse
from app.services.wishlist_service.wishlist_service import add_to_wishlist as svc_add, list_user_wishlist as svc_list, remove_wishlist as svc_remove
from app.dependencies.authentication import get_current_user, ensure_only_basic_user
from app.models.sqlalchemy_schemas.users import Users
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/wishlist", tags=["WISHLIST"])


# ============================================================================
# 🔹 CREATE - Add room to user's wishlist
# ============================================================================
@router.post("/", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def add_wishlist(
    payload: WishlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _basic_user_check: bool = Depends(ensure_only_basic_user),
):
    """Add item to wishlist - only available for basic/customer users"""
    # enforce ownership

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
async def list_wishlist(db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
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
async def delete_wishlist(wishlist_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    await svc_remove(db, wishlist_id, current_user.user_id)
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return {"message":"wishlist deleted successfully"}