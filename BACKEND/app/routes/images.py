# ==============================================================
# app/routes/images.py
# Purpose: REST API endpoints for Images management
# ==============================================================

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Security, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from app.dependencies.authentication import get_current_user, check_permission
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.utils.images_util import (
    create_image,
    get_images_for_entity,
    hard_delete_image,
    set_image_primary,
    get_images_for_offer,
)
from app.services.image_upload_service import save_uploaded_image
from app.utils.audit_util import log_audit
from pydantic import BaseModel

router = APIRouter(prefix="/images", tags=["Images"])


class ImageResponse(BaseModel):
    image_id: int
    entity_type: str
    entity_id: int
    image_url: str
    caption: Optional[str] = None
    is_primary: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# OFFER IMAGES - UPLOAD
# ============================================================
@router.post("/offers/{offer_id}/images", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_offer_image(
    offer_id: int,
    image: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: Optional[str] = Form("false"),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["OFFER_MANAGEMENT:WRITE"]),
):
    """Upload an image for an offer
    
    - **offer_id**: ID of the offer
    - **image**: Image file to upload
    - **caption**: Optional image caption
    - **is_primary**: String 'true' or 'false' - whether this is the primary image for the offer
    """
    try:
        # Convert string 'true'/'false' to boolean
        is_primary_bool = is_primary.lower() == 'true' if isinstance(is_primary, str) else bool(is_primary)
        
        image_url = await save_uploaded_image(image)
        image_record = await create_image(
            db,
            entity_type="offer",
            entity_id=offer_id,
            image_url=image_url,
            caption=caption,
            is_primary=is_primary_bool,
            uploaded_by=current_user.user_id,
        )
        new_val = ImageResponse.model_validate(image_record).model_dump()
        await log_audit(
            entity="offer_image",
            entity_id=f"offer:{offer_id}:image:{image_record.image_id}",
            action="INSERT",
            new_value=new_val
        )
        return ImageResponse.model_validate(image_record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================
# OFFER IMAGES - READ
# ============================================================
@router.get("/offers/{offer_id}/images", response_model=List[ImageResponse])
async def list_offer_images(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: Users = Depends(get_current_user),
):
    """Get all images for an offer"""
    items = await get_images_for_offer(db, offer_id)
    return [ImageResponse.model_validate(i) for i in items]


# ============================================================
# OFFER IMAGES - MARK PRIMARY
# ============================================================
@router.put("/offers/{offer_id}/images/{image_id}/primary", status_code=status.HTTP_200_OK)
async def mark_offer_image_primary(
    offer_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["OFFER_MANAGEMENT:WRITE"]),
):
    """Mark an image as primary for the offer"""
    await set_image_primary(db, image_id, requester_id=current_user.user_id)
    return {"message": "Image marked as primary"}


# ============================================================
# OFFER IMAGES - DELETE
# ============================================================
@router.delete("/offers/{offer_id}/images", status_code=status.HTTP_200_OK)
async def delete_offer_images(
    offer_id: int,
    image_ids: List[int] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["OFFER_MANAGEMENT:DELETE"]),
):
    """Delete images from an offer"""
    for image_id in image_ids:
        await hard_delete_image(db, image_id, requester_id=current_user.user_id)
    await db.commit()
    return {"message": f"Deleted {len(image_ids)} image(s)"}


# ============================================================
# OFFER IMAGES - BULK UPDATE (Add multiple images for offer update)
# ============================================================
@router.post("/offers/{offer_id}/images/bulk", response_model=List[ImageResponse], status_code=status.HTTP_201_CREATED)
async def bulk_upload_offer_images(
    offer_id: int,
    images: List[UploadFile] = File(...),
    primary_index: int = Form(0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["OFFER_MANAGEMENT:WRITE"]),
):
    """Upload multiple images for an offer (used in offer update)
    
    - **offer_id**: ID of the offer
    - **images**: List of image files to upload
    - **primary_index**: Index of the image to be marked as primary (0-based)
    """
    try:
        uploaded_images = []
        
        for idx, image in enumerate(images):
            if not image.filename:
                continue
                
            # Upload image to Cloudinary
            image_url = await save_uploaded_image(image)
            
            # Determine if this is the primary image
            is_primary = (idx == primary_index)
            
            # If marking as primary, unset primary on all other images for this offer
            if is_primary:
                await set_image_primary(db, None, requester_id=current_user.user_id, offer_id=offer_id)
            
            # Create image record
            image_record = await create_image(
                db,
                entity_type="offer",
                entity_id=offer_id,
                image_url=image_url,
                caption=None,
                is_primary=is_primary,
                uploaded_by=current_user.user_id,
            )
            
            uploaded_images.append(ImageResponse.model_validate(image_record))
            
            # Log audit
            new_val = ImageResponse.model_validate(image_record).model_dump()
            await log_audit(
                entity="offer_image",
                entity_id=f"offer:{offer_id}:image:{image_record.image_id}",
                action="INSERT",
                new_value=new_val
            )
        
        await db.commit()
        return uploaded_images
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


# ============================================================
# GENERIC IMAGES - UPLOAD
# ============================================================
@router.post("/upload", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    caption: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Upload an image for an entity (offer, review, room_type, issue, etc.)
    
    - **file**: Image file (JPG, PNG, GIF, WebP)
    - **entity_type**: Type of entity (offer, review, room_type, issue, etc.)
    - **entity_id**: ID of the entity
    - **caption**: Optional image caption
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    # Upload to Cloudinary
    try:
        image_url = await save_uploaded_image(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload failed: {str(e)}"
        )

    # Save image record to database
    image_record = await create_image(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        image_url=image_url,
        caption=caption,
        is_primary=False,
        uploaded_by=current_user.user_id,
    )

    return ImageResponse(
        image_id=image_record.image_id,
        entity_type=image_record.entity_type,
        entity_id=image_record.entity_id,
        image_url=image_record.image_url,
        caption=image_record.caption,
        is_primary=image_record.is_primary,
        created_at=image_record.created_at.isoformat() if image_record.created_at else None,
    )


# ============================================================
# READ
# ============================================================
@router.get("", response_model=List[ImageResponse])
async def get_images(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Get all images for an entity
    
    - **entity_type**: Type of entity (offer, review, room_type, issue, etc.)
    - **entity_id**: ID of the entity
    """
    images = await get_images_for_entity(db, entity_type, entity_id)
    return [
        ImageResponse(
            image_id=img.image_id,
            entity_type=img.entity_type,
            entity_id=img.entity_id,
            image_url=img.image_url,
            caption=img.caption,
            is_primary=img.is_primary,
            created_at=img.created_at.isoformat() if img.created_at else None,
        )
        for img in images
    ]


# ============================================================
# DELETE
# ============================================================
@router.delete("/{image_id}", status_code=status.HTTP_200_OK)
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Delete an image (only by uploader or admin with permissions)
    """
    await hard_delete_image(db, image_id, current_user.user_id)
    return {"message": "Image deleted successfully", "image_id": image_id}
