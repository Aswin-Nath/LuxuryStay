from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.sqlalchemy_schemas.wishlist import Wishlist
from app.models.sqlalchemy_schemas.rooms import RoomTypes, RoomTypeAmenityMap, RoomAmenities
from app.models.sqlalchemy_schemas.offers import Offers
from app.models.sqlalchemy_schemas.images import Images

# CRUD imports
from app.crud.wishlist import (
    create_wishlist_entry,
    get_wishlist_by_user_and_item,
    get_user_wishlist,
    get_wishlist_by_id,
    soft_delete_wishlist_entry,
)


# ============================================================================
# 🔹 HELPER - Get Primary Image URL
# ============================================================================

async def get_primary_image_url(db: AsyncSession, entity_type: str, entity_id: int) -> Optional[str]:
    """
    Fetch the primary image URL for a room type or offer.
    
    Args:
        db (AsyncSession): Database session
        entity_type (str): Either 'room_type' or 'offer'
        entity_id (int): The ID of the entity
    
    Returns:
        Optional[str]: Image URL if found, None otherwise
    """
    stmt = (
        select(Images.image_url)
        .where(
            Images.entity_type == entity_type,
            Images.entity_id == entity_id,
            Images.is_deleted == False,
            Images.is_primary == True
        )
        .limit(1)
    )
    
    result = await db.execute(stmt)
    image_url = result.scalars().first()
    return image_url


# ==========================================================
# 🔹 ADD TO WISHLIST
# ==========================================================

async def add_to_wishlist(db: AsyncSession, payload, current_user) -> Wishlist:

    wishlist_data = payload.model_dump()
    user_id = current_user.user_id
    room_type_id = wishlist_data.get("room_type_id")
    offer_id = wishlist_data.get("offer_id")

    # Validate that exactly one is provided
    if not room_type_id and not offer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either room_type_id or offer_id must be provided",
        )
    
    if room_type_id and offer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both room_type_id and offer_id",
        )

    # Check uniqueness
    existing_item = await get_wishlist_by_user_and_item(db, user_id, room_type_id, offer_id)
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already in wishlist",
        )

    # Create entry
    wishlist_entry = await create_wishlist_entry(db, user_id, room_type_id, offer_id)
    await db.commit()
    return wishlist_entry


# ==========================================================
# 🔹 LIST USER WISHLIST (ALL)
# ==========================================================

async def list_user_wishlist(
    db: AsyncSession, user_id: int, include_deleted: bool = False
) -> List[Wishlist]:
    """
    Retrieve all wishlist items for a user.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The ID of the user.
        include_deleted (bool): If True, includes soft-deleted wishlist items (default False).
    
    Returns:
        List[Wishlist]: All active (or all) wishlist entries for the user.
    """
    return await get_user_wishlist(db, user_id, include_deleted)


# ==========================================================
# 🔹 LIST USER WISHLIST ROOMS WITH DETAILS
# ==========================================================

async def list_user_wishlist_rooms(db: AsyncSession, user_id: int) -> List[dict]:
    """
    Retrieve all room-type wishlist items for a user with full room details.
    
    Returns room type details including type_name, price, amenities, etc.
    
    Args:
        db (AsyncSession): Database session
        user_id (int): The user ID
    
    Returns:
        List[dict]: Wishlist room entries with full room type details
    """
    stmt = (
        select(Wishlist, RoomTypes)
        .join(RoomTypes, Wishlist.room_type_id == RoomTypes.room_type_id)
        .where(
            Wishlist.user_id == user_id,
            Wishlist.is_deleted == False,
            Wishlist.wishlist_type == "room",
            RoomTypes.is_deleted == False
        )
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    rooms_data = []
    for wishlist_entry, room_type in rows:
        # Fetch amenities for this room type
        amenities_stmt = (
            select(RoomAmenities.amenity_name)
            .join(RoomTypeAmenityMap, RoomAmenities.amenity_id == RoomTypeAmenityMap.amenity_id)
            .where(RoomTypeAmenityMap.room_type_id == room_type.room_type_id)
        )
        amenities_result = await db.execute(amenities_stmt)
        amenities = [name[0] for name in amenities_result.all()]
        
        rooms_data.append({
            "wishlist_id": wishlist_entry.wishlist_id,
            "room_type_id": room_type.room_type_id,
            "type_name": room_type.type_name,
            "price_per_night": float(room_type.price_per_night),
            "description": room_type.description,
            "square_ft": room_type.square_ft,
            "max_adult_count": room_type.max_adult_count,
            "max_child_count": room_type.max_child_count,
            "amenities": amenities,
            "added_at": wishlist_entry.added_at,
            "primary_image": await get_primary_image_url(db, "room_type", room_type.room_type_id)
        })
    
    return rooms_data


# ==========================================================
# 🔹 LIST USER WISHLIST OFFERS WITH DETAILS
# ==========================================================

async def list_user_wishlist_offers(db: AsyncSession, user_id: int) -> List[dict]:
    """
    Retrieve all offer wishlist items for a user with full offer details.
    
    Returns offer details including offer_name, discount, room_types, validity dates, etc.
    
    Args:
        db (AsyncSession): Database session
        user_id (int): The user ID
    
    Returns:
        List[dict]: Wishlist offer entries with full offer details
    """
    stmt = (
        select(Wishlist, Offers)
        .join(Offers, Wishlist.offer_id == Offers.offer_id)
        .where(
            Wishlist.user_id == user_id,
            Wishlist.is_deleted == False,
            Wishlist.wishlist_type == "offer",
            Offers.is_deleted == False
        )
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    offers_data = []
    for wishlist_entry, offer in rows:
        # Fetch primary image for this offer
        primary_image = await get_primary_image_url(db, "offer", offer.offer_id)
        
        offers_data.append({
            "wishlist_id": wishlist_entry.wishlist_id,
            "offer_id": offer.offer_id,
            "offer_name": offer.offer_name,
            "description": offer.description,
            "discount_percent": float(offer.discount_percent),
            "valid_from": offer.valid_from,
            "valid_to": offer.valid_to,
            "room_types": offer.room_types,  # JSONB array
            "added_at": wishlist_entry.added_at,
            "primary_image": primary_image
        })
    
    return offers_data


# ==========================================================
# 🔹 REMOVE WISHLIST ITEM
# ==========================================================

async def remove_wishlist(db: AsyncSession, wishlist_id: int, user_id: int):
    """
    Remove a wishlist item by soft-deleting it.
    
    Soft-deletes a wishlist entry for a user. Validates that the user owns the wishlist item
    before deletion. The entry remains in the database marked as deleted for audit purposes.
    
    Args:
        db (AsyncSession): Database session for executing queries.
        wishlist_id (int): The ID of the wishlist item to remove.
        user_id (int): The ID of the current user (must own the item).
    
    Returns:
        dict: Confirmation message {"message": "Wishlist item removed"}.
    
    Raises:
        HTTPException (404): If wishlist item not found.
        HTTPException (403): If user does not own the wishlist item.
    """
    wishlist_entry = await get_wishlist_by_id(db, wishlist_id)
    if not wishlist_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    if wishlist_entry.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to remove this wishlist item",
        )

    await soft_delete_wishlist_entry(db, wishlist_entry)
    await db.commit()
    return {"message": "Wishlist item removed"}