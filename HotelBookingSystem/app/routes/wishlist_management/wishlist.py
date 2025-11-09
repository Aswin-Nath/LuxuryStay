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


@router.post("/", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def add_wishlist(
    payload: WishlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    _basic_user_check: bool = Depends(ensure_only_basic_user),
):
    """Add item to wishlist - only available for basic/customer users"""
    # enforce ownership

    obj = await svc_add(db, payload, current_user)
    # audit wishlist create
    try:
        new_val = WishlistResponse.model_validate(obj).model_dump()
        entity_id = f"wishlist:{getattr(obj, 'wishlist_id', None)}"
        await log_audit(entity="wishlist", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return WishlistResponse.model_validate(obj).model_dump()


@router.get("/", response_model=List[WishlistResponse])
async def list_wishlist(db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    cache_key = f"wishlist:user:{current_user.user_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list(db, current_user.user_id)
    result = [WishlistResponse.model_validate(i).model_dump() for i in items]
    await set_cached(cache_key, result, ttl=120)
    return result




@router.delete("/{wishlist_id}", status_code=status.HTTP_201_CREATED)
async def delete_wishlist(wishlist_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    await svc_remove(db, wishlist_id, current_user.user_id)
    # invalidate this user's wishlist cache
    await invalidate_pattern(f"wishlist:user:{current_user.user_id}:*")
    return {"message":"wishlist deleted successfully"}