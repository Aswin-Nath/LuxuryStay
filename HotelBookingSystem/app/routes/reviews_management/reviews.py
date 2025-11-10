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
    """
    Submit a new review for a completed booking.
    
    Creates a review for a room after checkout. Users can rate (1-5 stars) and provide
    comments. Reviews are attached to bookings and can include images via separate endpoint.
    One review per booking allowed. Draft reviews can be updated before finalization.
    
    Args:
        booking_id (int): The completed booking to review (user must own booking).
        room_type_id (Optional[int]): Room type being reviewed (optional).
        rating (int): Star rating (1-5).
        comment (Optional[str]): User's review text/feedback.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user creating review.
    
    Returns:
        ReviewResponse: Created review with review_id, rating, comment, timestamps.
    
    Raises:
        HTTPException (404): If booking_id not found or not owned by user.
        HTTPException (409): If review already exists for this booking.
    
    Side Effects:
        - Invalidates reviews cache pattern ("reviews:*").
        - Creates audit log entry.
        - Images uploaded separately via /reviews/{review_id}/images.
    """
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
    """
    Retrieve reviews (single or list with optional filters).
    
    Flexible GET endpoint supporting two modes:
    - **By review_id:** Returns single review with all attached images.
    - **By filters:** Returns list of reviews optionally filtered by booking_id, room_id, or user_id.
    
    Results are cached for 120 seconds to reduce database load. Images are included in responses.
    
    Args:
        review_id (Optional[int]): Query parameter - if provided, return specific review.
        booking_id (Optional[int]): Query parameter - filter reviews by booking.
        room_id (Optional[int]): Query parameter - filter reviews by room.
        user_id (Optional[int]): Query parameter - filter reviews by reviewer.
        db (AsyncSession): Database session dependency.
    
    Returns:
        ReviewResponse | List[ReviewResponse]: Single review or list with attached images.
    
    Raises:
        HTTPException (404): If review_id not found.
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
    """
    Add admin response to a customer review.
    
    Allows admin/manager to respond to customer reviews publicly. Response is visible to
    all users viewing the review. One response per review allowed. Useful for addressing
    concerns or thanking guests for feedback.
    
    **Authorization:** Requires non-basic user (admin/manager role).
    
    Args:
        review_id (int): The review ID to respond to.
        payload (AdminResponseCreate): Admin's response message.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated admin user.
        _ok (bool): Non-basic user check.
    
    Returns:
        ReviewResponse: Updated review with admin_response field populated.
    
    Raises:
        HTTPException (403): If user is basic user.
        HTTPException (404): If review_id not found.
    
    Side Effects:
        - Invalidates reviews cache pattern ("reviews:*").
        - Creates audit log entry.
    """
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
    """
    Update user's own review (rating and/or comment).
    
    Allows the reviewer to modify their rating or comment after submission. Only the review
    owner can edit. Admin response (if any) remains unchanged. Changes are timestamped for
    auditing. Useful for correcting typos or adjusting ratings after reflection.
    
    Args:
        review_id (int): The review ID to update (must own).
        payload (ReviewUpdate): Updated rating and/or comment.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (review owner).
    
    Returns:
        ReviewResponse: Updated review with new rating/comment and updated_at timestamp.
    
    Raises:
        HTTPException (403): If user doesn't own the review.
        HTTPException (404): If review_id not found.
    
    Side Effects:
        - Invalidates reviews cache pattern ("reviews:*").
        - Creates audit log entry.
        - Updates updated_at timestamp.
    """
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
    """
    Upload one or more images for a review.
    
    Attaches photos/screenshots to a review for visual context. Supports batch uploads with
    optional captions for each image. Images are stored via external provider and linked to
    the review. Maximum file size and format restrictions enforced by upload service.
    
    Args:
        review_id (int): The review to attach images to.
        files (List[UploadFile]): Image files to upload (must be images).
        captions (Optional[List[str]]): Optional captions for each image (matched by index).
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user (review owner).
    
    Returns:
        List[ImageResponse]: Created image records with URLs and captions.
    
    Raises:
        HTTPException (400): If file format invalid or too large.
        HTTPException (404): If review_id not found.
    
    Side Effects:
        - Uploads files to external storage.
        - Creates image records in database.
        - Invalidates review cache.
        - Creates audit log entry per image.
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
    """
    Retrieve all images attached to a review.
    
    Fetches the complete list of images/photos associated with a specific review. Includes
    URLs, captions, and uploader information. Useful for gallery views and detailed review pages.
    
    Args:
        review_id (int): The review to fetch images for.
        db (AsyncSession): Database session dependency.
    
    Returns:
        List[ImageResponse]: List of image records with URLs and metadata.
    
    Raises:
        HTTPException (404): If review_id not found (returns empty list by default).
    """
    items = await get_images_for_review(db, review_id)
    return [ImageResponse.model_validate(i) for i in items]


# ============================================================================
# 🔹 DELETE - Remove images from review
# ============================================================================
@router.delete("/{review_id}/images")
async def delete_review_images(review_id: int, image_ids: List[int], db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user), user_permissions: dict = Depends(get_user_permissions)):
    """
    Delete images from a review.
    
    Removes specified images from a review. Only the image uploader or users with
    ROOM_MANAGEMENT:WRITE permission can delete images. Images are permanently removed
    from storage and database.
    
    Args:
        review_id (int): The review containing images.
        image_ids (List[int]): JSON body with list of image_ids to delete.
        db (AsyncSession): Database session dependency.
        current_user (Users): Authenticated user.
        user_permissions (dict): Current user's permissions.
    
    Returns:
        dict: Confirmation with list of deleted image_ids and success message.
    
    Raises:
        HTTPException (400): If image_ids list is empty.
        HTTPException (403): If user not image uploader and lacks ROOM_MANAGEMENT:WRITE.
        HTTPException (404): If image_id not found.
    
    Side Effects:
        - Removes images from external storage.
        - Invalidates review cache.
        - Creates audit log entry per deletion.
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