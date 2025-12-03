# ==============================================================
# app/routes/offers.py
# Purpose: REST API endpoints for Offers management
# ==============================================================

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from app.dependencies.authentication import get_current_user
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    ConflictException,
)
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.schemas.pydantic_models.offers import (
    OfferCreate,
    OfferUpdate,
    OfferResponse,
    OfferListResponse,
)
from app.services.offers_service import (
    svc_create_offer,
    svc_get_offer,
    svc_list_offers,
    svc_get_active_offers_for_date,
    svc_get_offers_for_room_type,
    svc_update_offer,
    svc_toggle_offer_status,
    svc_delete_offer,
    svc_can_apply_offer,
    svc_apply_offer_to_booking,
)
from app.crud.rooms import fetch_all_room_types, get_room_type_counts
from datetime import date
from decimal import Decimal


class RoomTypeWithCount(BaseModel):
    """Room type with total count of rooms in hotel"""
    room_type_id: int
    type_name: str
    total_count: int
    price_per_night: float
    description: str


router = APIRouter(prefix="/offers", tags=["Offers"])


# ============================================================
# CREATE
# ============================================================
@router.post("/create", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: OfferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Create a new offer (Admin only)
    
    - **offer_name**: Unique name for the offer
    - **description**: Optional description
    - **discount_percent**: Base discount percentage (0-100)
    - **room_types**: Array with room_type_id, available_count, and discount_percent
    - **is_active**: Whether offer is active immediately
    - **valid_from / valid_to**: Date range when offer is valid
    - **max_uses**: Optional max usage limit
    """
    # TODO: Add permission check for ADMIN/OFFER_MANAGEMENT:WRITE
    return await svc_create_offer(db, payload)


# ============================================================
# READ - SPECIFIC ROUTES FIRST (before /{offer_id})
# ============================================================
@router.get("/room-types/with-counts", response_model=List[RoomTypeWithCount])
async def get_room_types_with_counts(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Get all room types with their total count of rooms in the hotel.
    Used for offer creation/editing to show admin how many rooms are available per type.
    
    Returns list of room types with total room count for each type.
    This is used to enforce the 5 rooms max rule per offer.
    """
    room_types = await fetch_all_room_types(db)
    room_counts = await get_room_type_counts(db)
    
    return [
        RoomTypeWithCount(
            room_type_id=rt.room_type_id,
            type_name=rt.type_name,
            total_count=room_counts.get(rt.room_type_id, 0),
            price_per_night=float(rt.price_per_night),
            description=rt.description or "",
        )
        for rt in room_types
    ]


@router.get("/active-offers/by-date", response_model=list[OfferResponse])
async def get_active_offers_for_date(
    check_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get all offers active on a specific date"""
    return await svc_get_active_offers_for_date(db, check_date)


@router.get("/room-type/{room_type_id}", response_model=list[OfferResponse])
async def get_offers_for_room_type(
    room_type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get all active offers applicable to a specific room type"""
    return await svc_get_offers_for_room_type(db, room_type_id)


# ============================================================
# READ - GENERIC ROUTES (after specific ones)
# ============================================================
@router.get("", response_model=list[OfferListResponse])
async def list_offers(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool = Query(None),
    min_discount: float = Query(None, ge=0, le=100),
    max_discount: float = Query(None, ge=0, le=100),
    valid_from: date = Query(None),
    valid_to: date = Query(None),
    room_type_id: int = Query(None),
):
    """
    List all offers with advanced filtering
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Number of records to return (max 500)
    - **is_active**: Filter by active status (true/false/null for all)
    - **min_discount**: Minimum discount percentage
    - **max_discount**: Maximum discount percentage
    - **valid_from**: Filter offers valid from this date
    - **valid_to**: Filter offers valid until this date
    - **room_type_id**: Filter offers containing this room type (single selection)
    """
    offers = await svc_list_offers(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        min_discount=min_discount,
        max_discount=max_discount,
        valid_from=valid_from,
        valid_to=valid_to,
        room_type_id=room_type_id,
        user_id=current_user.user_id,
    )
    return [
        OfferListResponse(
            offer_id=o.offer_id,
            offer_name=o.offer_name,
            description=o.description,
            discount_percent=o.discount_percent,
            is_active=o.is_active,
            valid_from=o.valid_from,
            valid_to=o.valid_to,
            current_uses=o.current_uses,
            max_uses=o.max_uses,
            is_saved_to_wishlist=o.is_saved_to_wishlist,
        )
        for o in offers
    ]


# ============================================================
# 📸 OFFER MEDIAS (Images for all offers)
# ============================================================
@router.get("/medias", response_model=dict)
async def get_offer_medias(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    is_active: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get images for all active offers in a single optimized call.
    
    Returns a dictionary mapping offer_id to their images.
    This endpoint optimizes the N+1 problem by fetching all offer images in one call
    instead of calling /images/{offer_id}/images separately for each offer.
    
    Returns:
        {
            "offer_id": {
                "images": [...]
            }
        }
    """
    from app.utils.images_util import get_images_for_entity
    
    # Get all active offers with filters
    offers = await svc_list_offers(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        user_id=current_user.user_id,
    )
    
    medias = {}
    
    # For each offer, fetch images
    for offer in offers:
        images = await get_images_for_entity(db, entity_type="offer", entity_id=offer.offer_id)
        
        medias[offer.offer_id] = {
            "images": [
                {
                    "image_id": img.image_id,
                    "image_url": img.image_url,
                    "is_primary": img.is_primary,
                    "caption": img.caption,
                }
                for img in images
            ]
        }
    
    return medias


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get offer details by ID with wishlist status"""
    return await svc_get_offer(db, offer_id, user_id=current_user.user_id)


@router.get("/{offer_id}/images", response_model=list)
async def get_offer_images(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get all images for an offer"""
    from app.utils.images_util import get_images_for_offer
    items = await get_images_for_offer(db, offer_id)
    return items


# ============================================================
# UPDATE
# ============================================================
@router.put("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: int,
    payload: OfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Update an offer (Admin only)
    
    All fields are optional - only provided fields will be updated
    """
    # TODO: Add permission check for ADMIN/OFFER_MANAGEMENT:WRITE
    return await svc_update_offer(db, offer_id, payload)


@router.patch("/{offer_id}/status", response_model=OfferResponse)
async def toggle_offer_status(
    offer_id: int,
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Toggle offer active/inactive status"""
    # TODO: Add permission check for ADMIN/OFFER_MANAGEMENT:WRITE
    return await svc_toggle_offer_status(db, offer_id, is_active)


# ============================================================
# DELETE
# ============================================================
@router.delete("/{offer_id}", status_code=status.HTTP_200_OK)
async def delete_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Soft delete an offer (Admin only)
    
    The offer will be marked as deleted but data remains in database
    """
    # TODO: Add permission check for ADMIN/OFFER_MANAGEMENT:DELETE
    return await svc_delete_offer(db, offer_id)


# ============================================================
# VALIDATION & BUSINESS LOGIC
# ============================================================
@router.get("/validate/can-apply", response_model=dict)
async def validate_offer_application(
    offer_id: int = Query(...),
    room_type_id: int = Query(...),
    check_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Check if an offer can be applied to a booking
    
    Returns: {"can_apply": true/false, "reason": "..."}
    """
    can_apply = await svc_can_apply_offer(db, offer_id, room_type_id, check_date)
    return {
        "can_apply": can_apply,
        "offer_id": offer_id,
        "room_type_id": room_type_id,
        "check_date": check_date,
    }


@router.post("/apply/calculate-discount", response_model=dict)
async def calculate_discount(
    offer_id: int = Query(...),
    room_type_id: int = Query(...),
    original_price: Decimal = Query(..., gt=0),
    check_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Calculate discounted price without applying it
    
    Returns: {"original_price": 5000, "discount_percent": 15, "discounted_price": 4250}
    """
    can_apply = await svc_can_apply_offer(db, offer_id, room_type_id, check_date)
    
    if not can_apply:
        raise ForbiddenException("This offer cannot be applied")
    
    from app.crud.offers import get_room_type_discount_in_offer
    
    discount_percent = await get_room_type_discount_in_offer(db, offer_id, room_type_id)
    discount_amount = original_price * Decimal(discount_percent / 100)
    discounted_price = original_price - discount_amount
    
    return {
        "original_price": float(original_price),
        "discount_percent": discount_percent,
        "discount_amount": float(discount_amount),
        "discounted_price": float(discounted_price),
    }
