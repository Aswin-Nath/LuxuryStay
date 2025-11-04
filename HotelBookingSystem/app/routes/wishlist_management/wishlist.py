from fastapi import APIRouter, Depends, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.wishlist import WishlistCreate, WishlistResponse
from app.services.wishlist_service.wishlist_service import add_to_wishlist as svc_add, list_user_wishlist as svc_list, remove_wishlist as svc_remove, get_wishlist_item as svc_get_item
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users


router = APIRouter(prefix="/api/wishlist", tags=["WISHLIST"])


@router.post("/", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def add_wishlist(payload: WishlistCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    # enforce ownership
    if payload.user_id != current_user.user_id:
        payload.user_id = current_user.user_id

    obj = await svc_add(db, payload)
    return WishlistResponse.model_validate(obj).model_dump()


@router.get("/", response_model=List[WishlistResponse])
async def list_wishlist(db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    items = await svc_list(db, current_user.user_id)
    return [WishlistResponse.model_validate(i).model_dump() for i in items]



@router.get("/item", response_model=WishlistResponse)
async def get_wishlist_item(room_type_id: int | None = None, offer_id: int | None = None, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Retrieve a single wishlist entry for the current user by room_type_id or offer_id."""
    obj = await svc_get_item(db, current_user.user_id, room_type_id, offer_id)
    if not obj:
        # Mirror patterns used elsewhere: raise 404 when not found
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")
    return WishlistResponse.model_validate(obj).model_dump()


@router.delete("/{wishlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wishlist(wishlist_id: int, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    await svc_remove(db, wishlist_id, current_user.user_id)
    return None
