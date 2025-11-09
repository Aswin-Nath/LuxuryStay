from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.reviews import ReviewCreate, ReviewResponse, AdminResponseCreate
from app.schemas.pydantic_models.reviews import ReviewUpdate
from app.services.reviews_service.reviews_service import (
    create_review as svc_create_review,
    get_review as svc_get_review,
    list_reviews as svc_list_reviews,
    admin_respond_review as svc_admin_respond,
    update_review_by_user as svc_update_review,
)
from app.dependencies.authentication import get_current_user, ensure_not_basic_user, get_user_permissions
from app.models.sqlalchemy_schemas.users import Users
from app.services.images_service.image_upload_service import save_uploaded_image
from app.services.room_service.images_service import create_image, hard_delete_image, get_images_for_review
from app.schemas.pydantic_models.images import ImageResponse
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.utils.audit_helper import log_audit


router = APIRouter(prefix="/reviews", tags=["REVIEWS"])


# ============================================================================
# 🔹 CREATE - Submit a new review for a booking
# ============================================================================
@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    booking_id: int = Form(...),
    room_type_id: Optional[int] = Form(None),
    rating: int = Form(...),
    comment: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # Build payload dict and create review
    payload = {
        "booking_id": booking_id,
        "room_type_id": room_type_id,
        "rating": rating,
        "comment": comment,
    }
    review_record = await svc_create_review(db, payload, current_user)
    # invalidate reviews caches
    await invalidate_pattern("reviews:*")
    # audit review create
    try:
        new_val = ReviewResponse.model_validate(review_record).model_dump()
        entity_id = f"review:{getattr(review_record, 'review_id', None)}"
        await log_audit(entity="review", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    # Images should be uploaded via the dedicated review images endpoints:
    # POST /api/reviews/{review_id}/images  -> for uploading
    # DELETE /api/reviews/{review_id}/images -> for removing images
    return ReviewResponse.model_validate(review_record)


# ============================================================================
# 🔹 READ - Fetch reviews (single or list with filters)
# ============================================================================
@router.get("/", response_model=Union[ReviewResponse, List[ReviewResponse]])
async def list_or_get_reviews(review_id: Optional[int] = None, booking_id: Optional[int] = None, room_id: Optional[int] = None, user_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """If review_id is provided return that single review (with images), otherwise return list (optionally filtered by booking_id).

    Each returned review will include attached images in the `images` field.
    """
    if review_id is not None:
        review_record = await svc_get_review(db, review_id)
        imgs = await get_images_for_review(db, review_id)
        img_resps = [ImageResponse.model_validate(i) for i in imgs]
        return ReviewResponse.model_validate(review_record).model_copy(update={"images": img_resps})

    cache_key = f"reviews:booking:{booking_id}:room:{room_id}:user:{user_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    items = await svc_list_reviews(db, booking_id=booking_id, room_id=room_id, user_id=user_id)
    out = []
    for i in items:
        imgs = await get_images_for_review(db, i.review_id)
        img_resps = [ImageResponse.model_validate(img) for img in imgs]
        out.append(ReviewResponse.model_validate(i).model_copy(update={"images": img_resps}))
    await set_cached(cache_key, out, ttl=120)
    return out


# ============================================================================
# 🔹 UPDATE - Add admin response to a review
# ============================================================================
@router.put("/{review_id}/respond", response_model=ReviewResponse)
async def respond_review(review_id: int, payload: AdminResponseCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), _ok: bool = Depends(ensure_not_basic_user)):
    # payload validated by Pydantic: {"admin_response": "..."}
    review_record = await svc_admin_respond(db, review_id, current_user, payload.admin_response)
    await invalidate_pattern("reviews:*")
    # audit admin response
    try:
        new_val = ReviewResponse.model_validate(review_record).model_dump()
        entity_id = f"review:{getattr(review_record, 'review_id', None)}"
        await log_audit(entity="review", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return ReviewResponse.model_validate(review_record)


# ============================================================================
# 🔹 UPDATE - Modify user's own review (rating/comment)
# ============================================================================
@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(review_id: int, payload: ReviewUpdate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Allow the authenticated reviewer to update their review's rating/comment."""
    review_record = await svc_update_review(db, review_id, payload, current_user)
    await invalidate_pattern("reviews:*")
    # audit user update
    try:
        new_val = ReviewResponse.model_validate(review_record).model_dump()
        entity_id = f"review:{getattr(review_record, 'review_id', None)}"
        await log_audit(entity="review", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass
    return ReviewResponse.model_validate(review_record)


# ============================================================================
# 🔹 CREATE - Upload images for a review
# ============================================================================
@router.post("/{review_id}/images", response_model=List[ImageResponse], status_code=status.HTTP_201_CREATED)
async def add_review_image(
    review_id: int,
    files: List[UploadFile] = File(...),
    captions: Optional[List[str]] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Upload one or more images for a review.

    captions may be provided as repeated form fields (`-F "captions=one" -F "captions=two"`) and
    will be applied to files by index. If there are fewer captions than files, remaining captions are None.
    """
    images = []
    for idx, file in enumerate(files):
        # upload to external provider
        url = await save_uploaded_image(file)
        caption = None
        if captions and idx < len(captions):
            caption = captions[idx]
        image_record = await create_image(db, entity_type="review", entity_id=review_id, image_url=url, caption=caption, uploaded_by=current_user.user_id)
        images.append(image_record)
        # audit each image created
        try:
            new_val = ImageResponse.model_validate(image_record).model_dump()
            entity_id = f"review:{review_id}:image:{getattr(image_record, 'image_id', None)}"
            await log_audit(entity="review_image", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
        except Exception:
            pass

    # invalidate caches for this review
    await invalidate_pattern(f"reviews:*{review_id}*")
    return [ImageResponse.model_validate(i) for i in images]


# ============================================================================
# 🔹 READ - Fetch all images for a review
# ============================================================================
@router.get("/{review_id}/images", response_model=List[ImageResponse])
async def list_review_images(review_id: int, db: AsyncSession = Depends(get_db)):
    items = await get_images_for_review(db, review_id)
    return [ImageResponse.model_validate(i) for i in items]


# ============================================================================
# 🔹 DELETE - Remove images from review
# ============================================================================
@router.delete("/{review_id}/images")
async def delete_review_images(review_id: int, image_ids: List[int], db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), user_permissions: dict = Depends(get_user_permissions)):
    """Delete specified image ids attached to a review. Only the uploader/review-owner or ROOM_MANAGEMENT.WRITE may delete.

    Caller must provide a list of image_ids (JSON body).
    """
    if not image_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_ids is required")
    deleted = []
    for img_id in image_ids:
        await hard_delete_image(db, img_id, requester_id=current_user.user_id, requester_permissions=user_permissions)
        deleted.append(img_id)
    # invalidate caches for this review
    await invalidate_pattern(f"reviews:*{review_id}*")
    return {"deleted": deleted, "message": "Images deleted"}