# ==============================================================
# app/services/offers_service.py
# Purpose: Business logic for Offers
# ==============================================================

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.crud.offers import (
    insert_offer,
    fetch_offer_by_id,
    fetch_all_offers,
    fetch_active_offers_for_date,
    fetch_offer_by_name,
    fetch_offers_by_room_type,
    update_offer,
    increment_offer_usage,
    toggle_offer_status,
    soft_delete_offer,
    check_offer_usage_limit,
    is_offer_valid_for_date,
    get_room_type_discount_in_offer,
    check_offer_has_active_bookings,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    BadRequestException,
    ForbiddenException,
)
from app.schemas.pydantic_models.offers import OfferCreate, OfferUpdate, OfferResponse
from app.models.sqlalchemy_schemas.rooms import RoomTypes
from datetime import date
from typing import Optional, List
from decimal import Decimal


# ============================================================
# HELPER FUNCTIONS
# ============================================================
async def _enrich_offer_room_types(db: AsyncSession, offer) -> None:
    """Enrich offer's room_types with pricing and names from database"""
    if offer.room_types:
        for room_type_config in offer.room_types:
            room_type_id = room_type_config.get('room_type_id')
            
            # Fetch room type details
            stmt = select(RoomTypes).where(
                (RoomTypes.room_type_id == room_type_id) &
                (RoomTypes.is_deleted.is_(False))
            )
            result = await db.execute(stmt)
            room_type = result.scalars().first()
            
            if room_type:
                # Add type_name and price_per_night to room_type_config
                room_type_config['type_name'] = room_type.type_name
                room_type_config['price_per_night'] = float(room_type.price_per_night)


# ============================================================
# CREATE
# ============================================================
async def svc_create_offer(db: AsyncSession, payload: OfferCreate) -> OfferResponse:
    """
    Create a new offer with validation
    - Check offer name uniqueness
    - Validate date range
    - Ensure room_types list is valid
    """
    # Check if offer name already exists
    existing = await fetch_offer_by_name(db, payload.offer_name)
    if existing:
        raise ConflictException(f"Offer '{payload.offer_name}' already exists")
    
    # Validate date range
    if payload.valid_from >= payload.valid_to:
        raise BadRequestException("valid_from must be before valid_to")
    
    # Validate room_types array
    if not payload.room_types or len(payload.room_types) == 0:
        raise BadRequestException("At least one room type must be specified")
    
    # Create offer
    # Convert Decimal to float for JSON serialization in JSONB column
    room_types_data = []
    for rt in payload.room_types:
        rt_dict = rt.model_dump()
        rt_dict['discount_percent'] = float(rt_dict['discount_percent'])
        room_types_data.append(rt_dict)
    
    offer_data = {
        "offer_name": payload.offer_name,
        "description": payload.description,
        "discount_percent": float(payload.discount_percent),
        "room_types": room_types_data,
        "is_active": payload.is_active,
        "valid_from": payload.valid_from,
        "valid_to": payload.valid_to,
        "max_uses": payload.max_uses,
        "current_uses": 0,
        "is_deleted": False,
    }
    
    offer = await insert_offer(db, offer_data)
    await db.commit()
    
    return OfferResponse.model_validate(offer)


# ============================================================
# READ
# ============================================================
async def svc_get_offer(db: AsyncSession, offer_id: int, user_id: Optional[int] = None) -> OfferResponse:
    """Get offer by ID with enriched room type details and wishlist status"""
    from app.crud.wishlist import get_wishlist_by_user_and_item
    
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        raise NotFoundException(f"Offer {offer_id} not found")
    
    # Enrich room_types with pricing and names
    await _enrich_offer_room_types(db, offer)
    
    # Check wishlist status if user_id provided
    is_saved = False
    if user_id:
        wishlist_entry = await get_wishlist_by_user_and_item(
            db,
            user_id=user_id,
            offer_id=offer_id
        )
        is_saved = wishlist_entry is not None
    
    # Convert to response and add wishlist status
    response = OfferResponse.model_validate(offer)
    response.is_saved_to_wishlist = is_saved
    
    return response


async def svc_list_offers(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    min_discount: Optional[float] = None,
    max_discount: Optional[float] = None,
    valid_from: Optional[date] = None,
    valid_to: Optional[date] = None,
    room_type_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> List[OfferResponse]:
    """List offers with advanced filtering (AND-based) and wishlist status"""
    from app.crud.wishlist import get_wishlist_by_user_and_item
    
    offers = await fetch_all_offers(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        min_discount=min_discount,
        max_discount=max_discount,
        valid_from=valid_from,
        valid_to=valid_to,
        room_type_id=room_type_id,
    )
    # Enrich all offers with room type details
    response_list = []
    for offer in offers:
        await _enrich_offer_room_types(db, offer)
        response = OfferResponse.model_validate(offer)
        
        # Check wishlist status if user_id provided
        if user_id:
            wishlist_entry = await get_wishlist_by_user_and_item(
                db,
                user_id=user_id,
                offer_id=offer.offer_id
            )
            response.is_saved_to_wishlist = wishlist_entry is not None
            if wishlist_entry:
                response.wishlist_id = wishlist_entry.wishlist_id
        
        response_list.append(response)
    
    return response_list


async def svc_get_active_offers_for_date(db: AsyncSession, check_date: date, user_id: Optional[int] = None) -> List[OfferResponse]:
    """Get all offers active on a specific date with wishlist status"""
    from app.crud.wishlist import get_wishlist_by_user_and_item
    
    offers = await fetch_active_offers_for_date(db, check_date)
    response_list = []
    for offer in offers:
        await _enrich_offer_room_types(db, offer)
        response = OfferResponse.model_validate(offer)
        
        # Check wishlist status if user_id provided
        if user_id:
            wishlist_entry = await get_wishlist_by_user_and_item(
                db,
                user_id=user_id,
                offer_id=offer.offer_id
            )
            response.is_saved_to_wishlist = wishlist_entry is not None
        
        response_list.append(response)
    
    return response_list


async def svc_get_offers_for_room_type(db: AsyncSession, room_type_id: int, user_id: Optional[int] = None) -> List[OfferResponse]:
    """Get all active offers for a specific room type with wishlist status"""
    from app.crud.wishlist import get_wishlist_by_user_and_item
    
    offers = await fetch_offers_by_room_type(db, room_type_id)
    response_list = []
    for offer in offers:
        await _enrich_offer_room_types(db, offer)
        response = OfferResponse.model_validate(offer)
        
        # Check wishlist status if user_id provided
        if user_id:
            wishlist_entry = await get_wishlist_by_user_and_item(
                db,
                user_id=user_id,
                offer_id=offer.offer_id
            )
            response.is_saved_to_wishlist = wishlist_entry is not None
        
        response_list.append(response)
    
    return response_list


# ============================================================
# UPDATE
# ============================================================
async def svc_update_offer(db: AsyncSession, offer_id: int, payload: OfferUpdate) -> OfferResponse:
    """
    Update an offer
    - Validate date range if dates are being updated
    - Check name uniqueness if name is being changed
    """
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        raise NotFoundException(f"Offer {offer_id} not found")
    
    # Build update data
    update_data = {}
    
    if payload.offer_name is not None:
        # Check uniqueness if name is being changed
        if payload.offer_name != offer.offer_name:
            existing = await fetch_offer_by_name(db, payload.offer_name)
            if existing:
                raise ConflictException(f"Offer '{payload.offer_name}' already exists")
        update_data["offer_name"] = payload.offer_name
    
    if payload.description is not None:
        update_data["description"] = payload.description
    
    if payload.discount_percent is not None:
        update_data["discount_percent"] = payload.discount_percent
    
    if payload.room_types is not None:
        if len(payload.room_types) == 0:
            raise BadRequestException("At least one room type must be specified")
        # Convert Decimal values to float to make them JSON serializable
        room_types_list = []
        for rt in payload.room_types:
            rt_dict = rt.model_dump()
            # Convert all numeric fields to float for JSON serialization
            if 'discount_percent' in rt_dict and rt_dict['discount_percent'] is not None:
                rt_dict['discount_percent'] = float(rt_dict['discount_percent'])
            room_types_list.append(rt_dict)
        update_data["room_types"] = room_types_list
    
    if payload.is_active is not None:
        update_data["is_active"] = payload.is_active
    
    if payload.valid_from is not None or payload.valid_to is not None:
        valid_from = payload.valid_from or offer.valid_from
        valid_to = payload.valid_to or offer.valid_to
        
        if valid_from >= valid_to:
            raise BadRequestException("valid_from must be before valid_to")
        
        update_data["valid_from"] = valid_from
        update_data["valid_to"] = valid_to
    
    if payload.max_uses is not None:
        update_data["max_uses"] = payload.max_uses
    
    updated_offer = await update_offer(db, offer_id, update_data)
    await db.commit()
    
    return OfferResponse.model_validate(updated_offer)


async def svc_toggle_offer_status(db: AsyncSession, offer_id: int, is_active: bool) -> OfferResponse:
    """Toggle offer active/inactive status"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        raise NotFoundException(f"Offer {offer_id} not found")
    
    updated = await toggle_offer_status(db, offer_id, is_active)
    await db.commit()
    
    return OfferResponse.model_validate(updated)


# ============================================================
# DELETE
# ============================================================
async def svc_delete_offer(db: AsyncSession, offer_id: int) -> dict:
    """Soft delete an offer - validates no active bookings using this offer"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        raise NotFoundException(f"Offer {offer_id} not found")
    
    # Check if offer is being used in active bookings
    has_active_bookings = await check_offer_has_active_bookings(db, offer_id)
    if has_active_bookings:
        raise ConflictException(
            "Cannot delete offer with active bookings. Please ensure all bookings using this offer are checked out or canceled."
        )
    
    deleted = await soft_delete_offer(db, offer_id)
    if not deleted:
        raise ConflictException("Failed to delete offer")
    
    await db.commit()
    
    return {"message": f"Offer {offer_id} deleted successfully", "offer_id": offer_id}


# ============================================================
# VALIDATION & BUSINESS LOGIC
# ============================================================
async def svc_can_apply_offer(
    db: AsyncSession,
    offer_id: int,
    room_type_id: int,
    check_date: date
) -> bool:
    """
    Check if an offer can be applied to a booking
    - Offer exists and not deleted
    - Offer is active
    - Offer is valid for the check-in date
    - Offer has available usage
    - Room type is in the offer's room_types list
    """
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return False
    
    # Check if valid for date
    if not await is_offer_valid_for_date(db, offer_id, check_date):
        return False
    
    # Check usage limit
    if not await check_offer_usage_limit(db, offer_id):
        return False
    
    # Check if room_type is in offer
    discount = await get_room_type_discount_in_offer(db, offer_id, room_type_id)
    return discount is not None


async def svc_apply_offer_to_booking(
    db: AsyncSession,
    offer_id: int,
    room_type_id: int,
    original_price: Decimal,
    check_date: date
) -> Decimal:
    """
    Apply offer discount to a booking price
    Returns the discounted price
    """
    # Validate offer can be applied
    can_apply = await svc_can_apply_offer(db, offer_id, room_type_id, check_date)
    if not can_apply:
        raise ForbiddenException("This offer cannot be applied to this booking")
    
    # Get discount percentage for this room type
    discount_percent = await get_room_type_discount_in_offer(db, offer_id, room_type_id)
    if discount_percent is None:
        raise BadRequestException("Room type not found in offer")
    
    # Calculate discount amount
    discount_amount = original_price * Decimal(discount_percent / 100)
    discounted_price = original_price - discount_amount
    
    # Increment usage
    await increment_offer_usage(db, offer_id)
    await db.commit()
    
    return discounted_price
