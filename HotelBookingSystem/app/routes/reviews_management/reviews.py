from fastapi import APIRouter, Depends, status
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.models.pydantic_models.reviews import ReviewCreate, ReviewResponse, AdminResponseCreate
from app.models.pydantic_models.reviews import ReviewUpdate
from app.services.reviews_service.reviews_service import (
    create_review as svc_create_review,
    get_review as svc_get_review,
    list_reviews as svc_list_reviews,
    admin_respond_review as svc_admin_respond,
    update_review_by_user as svc_update_review,
)
from app.dependencies.authentication import get_current_user, ensure_not_basic_user
from app.models.sqlalchemy_schemas.users import Users


router = APIRouter(prefix="/api/reviews", tags=["REVIEWS"])


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_create_review(db, payload, current_user)
    # return Pydantic response via orm_mode
    return ReviewResponse.model_validate(obj)


@router.get("/", response_model=Union[ReviewResponse, List[ReviewResponse]])
async def list_or_get_reviews(review_id: Optional[int] = None, booking_id: Optional[int] = None, room_id: Optional[int] = None, user_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """If review_id is provided return that single review, otherwise return list (optionally filtered by booking_id)."""
    if review_id is not None:
        obj = await svc_get_review(db, review_id)
        return ReviewResponse.model_validate(obj)
    items = await svc_list_reviews(db, booking_id=booking_id, room_id=room_id, user_id=user_id)
    return [ReviewResponse.model_validate(i) for i in items]


@router.put("/{review_id}/respond", response_model=ReviewResponse)
async def respond_review(review_id: int, payload: AdminResponseCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), _ok: bool = Depends(ensure_not_basic_user)):
    # payload validated by Pydantic: {"admin_response": "..."}
    obj = await svc_admin_respond(db, review_id, current_user, payload.admin_response)
    return ReviewResponse.model_validate(obj)


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(review_id: int, payload: ReviewUpdate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Allow the authenticated reviewer to update their review's rating/comment."""
    obj = await svc_update_review(db, review_id, payload, current_user)
    return ReviewResponse.model_validate(obj)