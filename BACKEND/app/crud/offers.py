# ==============================================================
# app/crud/offers.py
# Purpose: CRUD operations for Offers
# ==============================================================

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select, and_, or_
from app.models.sqlalchemy_schemas.offers import Offers
from app.models.sqlalchemy_schemas.bookings import Bookings
from datetime import date, datetime
from typing import Optional, List


# ============================================================
# CREATE
# ============================================================
async def insert_offer(db: AsyncSession, offer_data: dict) -> Offers:
    """Create a new offer"""
    offer = Offers(**offer_data)
    db.add(offer)
    await db.flush()
    return offer


# ============================================================
# READ
# ============================================================
async def fetch_offer_by_id(db: AsyncSession, offer_id: int) -> Optional[Offers]:
    """Fetch offer by ID (active and non-deleted)"""
    stmt = select(Offers).where(
        and_(
            Offers.offer_id == offer_id,
            Offers.is_deleted.is_(False)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def fetch_all_offers(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    min_discount: Optional[float] = None,
    max_discount: Optional[float] = None,
    valid_from: Optional[date] = None,
    valid_to: Optional[date] = None,
    room_type_id: Optional[int] = None,
) -> List[Offers]:
    """Fetch all offers with advanced filtering (AND-based)"""
    stmt = select(Offers).where(Offers.is_deleted.is_(False))
    
    # Filter by active status
    if is_active is not None:
        stmt = stmt.where(Offers.is_active.is_(is_active))
    
    
    # Filter by discount percentage range
    if min_discount is not None:
        stmt = stmt.where(Offers.discount_percent >= min_discount)
    if max_discount is not None:
        stmt = stmt.where(Offers.discount_percent <= max_discount)
    
    # Filter by date range
    if valid_from is not None:
        stmt = stmt.where(Offers.valid_from >= valid_from)
    if valid_to is not None:
        stmt = stmt.where(Offers.valid_to <= valid_to)
    
    # Filter by room type (offers containing this room type)
    # room_types is stored as JSONB, so we use @> operator
    if room_type_id is not None:
        stmt = stmt.where(
            Offers.room_types.contains([{"room_type_id": room_type_id}])
        )
    
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def fetch_active_offers_for_date(db: AsyncSession, check_date: date) -> List[Offers]:
    """Fetch offers active on a specific date"""
    stmt = select(Offers).where(
        and_(
            Offers.is_deleted.is_(False),
            Offers.is_active.is_(True),
            Offers.valid_from <= check_date,
            Offers.valid_to >= check_date
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def fetch_offer_by_name(db: AsyncSession, offer_name: str) -> Optional[Offers]:
    """Fetch offer by name"""
    stmt = select(Offers).where(
        and_(
            Offers.offer_name == offer_name,
            Offers.is_deleted.is_(False)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def fetch_offers_by_room_type(db: AsyncSession, room_type_id: int) -> List[Offers]:
    """Fetch all active offers applicable to a room type"""
    stmt = select(Offers).where(
        and_(
            Offers.is_deleted.is_(False),
            Offers.is_active.is_(True),
            # Check if room_type_id exists in room_types JSONB array
            Offers.room_types.astext.contains(f'"room_type_id": {room_type_id}')
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================
# UPDATE
# ============================================================
async def update_offer(db: AsyncSession, offer_id: int, update_data: dict) -> Optional[Offers]:
    """Update an offer"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return None
    
    for key, value in update_data.items():
        if value is not None:
            setattr(offer, key, value)
    
    await db.flush()
    # Refresh to reload all attributes properly and avoid greenlet issues
    await db.refresh(offer)
    return offer


async def increment_offer_usage(db: AsyncSession, offer_id: int) -> Optional[Offers]:
    """Increment the current_uses counter for an offer"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return None
    
    offer.current_uses += 1
    await db.flush()
    return offer


async def toggle_offer_status(db: AsyncSession, offer_id: int, is_active: bool) -> Optional[Offers]:
    """Toggle offer active/inactive status"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return None
    
    offer.is_active = is_active
    db.add(offer)
    await db.flush()
    await db.refresh(offer)
    return offer


# ============================================================
# DELETE (Soft Delete)
# ============================================================
async def soft_delete_offer(db: AsyncSession, offer_id: int) -> Optional[Offers]:
    """Soft delete an offer - checks for active bookings first"""
    # Check if offer is being used in active bookings
    has_active_bookings = await check_offer_has_active_bookings(db, offer_id)
    if has_active_bookings:
        return None  # Return None to indicate cannot delete
    
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return None
    
    offer.is_deleted = True
    await db.flush()
    return offer


async def hard_delete_offer(db: AsyncSession, offer_id: int) -> bool:
    """Hard delete an offer (use with caution)"""
    stmt = select(Offers).where(Offers.offer_id == offer_id)
    result = await db.execute(stmt)
    offer = result.scalars().first()
    
    if not offer:
        return False
    
    await db.delete(offer)
    await db.flush()
    return True


# ============================================================
# VALIDATION HELPERS
# ============================================================
async def check_offer_has_active_bookings(db: AsyncSession, offer_id: int) -> bool:
    """Check if offer is currently being used in any active (non-checked-out, non-canceled) bookings"""
    stmt = select(Bookings).where(
        and_(
            Bookings.offer_id == offer_id,
            Bookings.is_deleted.is_(False),
            Bookings.status.notIn(['Cancelled','Checked_out'])  # Active statuses
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def check_offer_usage_limit(db: AsyncSession, offer_id: int) -> bool:
    """Check if offer can still be used (hasn't reached max_uses)"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return False
    
    # No limit if max_uses is None
    if offer.max_uses is None:
        return True
    
    return offer.current_uses < offer.max_uses


async def is_offer_valid_for_date(db: AsyncSession, offer_id: int, check_date: date) -> bool:
    """Check if offer is valid on a specific date"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return False
    
    return (
        offer.is_active
        and offer.valid_from <= check_date
        and offer.valid_to >= check_date
    )


async def get_room_type_discount_in_offer(
    db: AsyncSession,
    offer_id: int,
    room_type_id: int
) -> Optional[float]:
    """Get the discount percentage for a specific room type in an offer"""
    offer = await fetch_offer_by_id(db, offer_id)
    if not offer:
        return None
    
    # room_types is a list of dicts: [{"room_type_id": 1, "available_count": 5, "discount_percent": 15.50}, ...]
    for room_offer in offer.room_types:
        if room_offer.get("room_type_id") == room_type_id:
            return float(room_offer.get("discount_percent", offer.discount_percent))
    
    return None
