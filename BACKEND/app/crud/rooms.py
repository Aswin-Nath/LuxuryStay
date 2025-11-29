from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# ==========================================================
# 🧱 MODELS
# ==========================================================
from app.models.sqlalchemy_schemas.rooms import (
    Rooms,
    RoomTypes,
    RoomAmenities,
    RoomTypeAmenityMap,
)

# ==========================================================
# 🔹 ROOM TYPES CRUD
# ==========================================================
async def insert_room_type(db: AsyncSession, data: dict) -> RoomTypes:
    record = RoomTypes(**data)
    db.add(record)
    await db.flush()
    return record


async def fetch_room_type_by_id(db: AsyncSession, room_type_id: int) -> Optional[RoomTypes]:
    res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
    return res.scalars().first()


async def fetch_room_type_by_name(db: AsyncSession, type_name: str) -> Optional[RoomTypes]:
    res = await db.execute(select(RoomTypes).where(RoomTypes.type_name == type_name))
    return res.scalars().first()


async def fetch_all_room_types(db: AsyncSession) -> List[RoomTypes]:
    stmt = select(RoomTypes).where(RoomTypes.is_deleted.is_(False))
    res = await db.execute(stmt)
    return res.scalars().all()


async def update_room_type_by_id(db: AsyncSession, room_type_id: int, updates: dict) -> None:
    if updates:
        await db.execute(
            update(RoomTypes)
            .where(RoomTypes.room_type_id == room_type_id)
            .values(**updates)
        )
    await db.flush()


async def mark_room_type_deleted(db: AsyncSession, room_type_id: int) -> None:
    await db.execute(
        update(RoomTypes)
        .where(RoomTypes.room_type_id == room_type_id)
        .values(is_deleted=True)
    )
    await db.flush()


# ==========================================================
# 🔹 ROOMS CRUD
# ==========================================================
async def insert_room(db: AsyncSession, data: dict) -> Rooms:
    record = Rooms(**data)
    db.add(record)
    await db.flush()
    return record


async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
	res = await db.execute(
		select(Rooms)
		.options(selectinload(Rooms.room_type))
		.where(Rooms.room_id == room_id)
	)
	return res.scalars().first()


async def fetch_room_by_number(db: AsyncSession, room_no: str, include_deleted: bool = False) -> Optional[Rooms]:
	stmt = select(Rooms).options(selectinload(Rooms.room_type)).where(Rooms.room_no == room_no)
	if not include_deleted:
		stmt = stmt.where(Rooms.is_deleted.is_(False))
	res = await db.execute(stmt)
	return res.scalars().first()


async def fetch_rooms_filtered(
    db: AsyncSession,
    room_type_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    is_freezed: Optional[bool] = None,
) -> List[Rooms]:
	stmt = select(Rooms).options(selectinload(Rooms.room_type))
	if room_type_id is not None:
		stmt = stmt.where(Rooms.room_type_id == room_type_id)
	if status_filter is not None:
		stmt = stmt.where(Rooms.room_status == status_filter)
	if is_freezed is not None:
		if is_freezed:
			stmt = stmt.where(Rooms.freeze_reason.isnot(None))
		else:
			stmt = stmt.where(Rooms.freeze_reason.is_(None))

	res = await db.execute(stmt)
	return res.scalars().all()


async def fetch_rooms_by_type_id(db: AsyncSession, room_type_id: int) -> List[Rooms]:
	"""Fetch all rooms of a specific room type"""
	stmt = select(Rooms).where(
		(Rooms.room_type_id == room_type_id) & 
		(Rooms.is_deleted.is_(False))
	)
	res = await db.execute(stmt)
	return res.scalars().all()


async def update_room_by_id(db: AsyncSession, room_id: int, updates: dict) -> None:
    if updates:
        await db.execute(
            update(Rooms)
            .where(Rooms.room_id == room_id)
            .values(**updates)
        )
    await db.flush()


async def soft_delete_room(db: AsyncSession, room_id: int) -> None:
    await db.execute(
        update(Rooms)
        .where(Rooms.room_id == room_id)
        .values(is_deleted=True)
    )
    await db.flush()


# ==========================================================
# 🔹 AMENITIES CRUD
# ==========================================================
async def insert_amenity(db: AsyncSession, data: dict) -> RoomAmenities:
    record = RoomAmenities(**data)
    db.add(record)
    await db.flush()
    return record


async def fetch_all_amenities(db: AsyncSession) -> List[RoomAmenities]:
    res = await db.execute(select(RoomAmenities))
    return res.scalars().all()


async def fetch_amenity_by_id(db: AsyncSession, amenity_id: int) -> Optional[RoomAmenities]:
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_id == amenity_id))
    return res.scalars().first()


async def fetch_amenity_by_name(db: AsyncSession, amenity_name: str) -> Optional[RoomAmenities]:
    res = await db.execute(select(RoomAmenities).where(RoomAmenities.amenity_name == amenity_name))
    return res.scalars().first()


async def remove_amenity(db: AsyncSession, amenity: RoomAmenities) -> None:
    await db.delete(amenity)
    await db.flush()


async def update_amenity_by_id(db: AsyncSession, amenity_id: int, updates: dict) -> None:
    if updates:
        await db.execute(
            update(RoomAmenities)
            .where(RoomAmenities.amenity_id == amenity_id)
            .values(**updates)
        )


# ==========================================================
# 🔹 ROOM TYPE-AMENITY MAP CRUD
# ==========================================================
async def insert_room_type_amenity_map(db: AsyncSession, data: dict) -> RoomTypeAmenityMap:
    """Map an amenity to a room type"""
    record = RoomTypeAmenityMap(**data)
    db.add(record)
    await db.flush()
    return record


async def fetch_amenities_by_room_type_id(db: AsyncSession, room_type_id: int) -> List[RoomAmenities]:
    """Get all amenities for a specific room type"""
    res = await db.execute(
        select(RoomAmenities)
        .join(RoomTypeAmenityMap, RoomTypeAmenityMap.amenity_id == RoomAmenities.amenity_id)
        .where(RoomTypeAmenityMap.room_type_id == room_type_id)
    )
    return res.scalars().all()


async def fetch_room_types_by_amenity_id(db: AsyncSession, amenity_id: int) -> List[RoomTypes]:
    """Get all room types that have a specific amenity"""
    res = await db.execute(
        select(RoomTypes)
        .join(RoomTypeAmenityMap, RoomTypeAmenityMap.room_type_id == RoomTypes.room_type_id)
        .where(RoomTypeAmenityMap.amenity_id == amenity_id)
        .where(RoomTypes.is_deleted.is_(False))
    )
    return res.scalars().all()


async def delete_room_type_amenity_map(db: AsyncSession, room_type_id: int, amenity_id: int) -> None:
    """Delete a specific amenity mapping from a room type"""
    await db.execute(
        delete(RoomTypeAmenityMap)
        .where(RoomTypeAmenityMap.room_type_id == room_type_id)
        .where(RoomTypeAmenityMap.amenity_id == amenity_id)
        .execution_options(synchronize_session=False)
    )
    await db.flush()


async def delete_all_amenities_for_room_type(db: AsyncSession, room_type_id: int) -> None:
    """Delete all amenity mappings for a room type"""
    await db.execute(
        delete(RoomTypeAmenityMap)
        .where(RoomTypeAmenityMap.room_type_id == room_type_id)
        .execution_options(synchronize_session=False)
    )
    await db.flush()


async def fetch_rooms_by_amenity_id(db: AsyncSession, amenity_id: int) -> List[Rooms]:
    """Get all rooms that have a specific amenity (through room type)"""
    res = await db.execute(
        select(Rooms)
        .join(RoomTypes, Rooms.room_type_id == RoomTypes.room_type_id)
        .join(RoomTypeAmenityMap, RoomTypeAmenityMap.room_type_id == RoomTypes.room_type_id)
        .where(RoomTypeAmenityMap.amenity_id == amenity_id)
        .where(Rooms.is_deleted.is_(False))
    )
    return res.scalars().all()


async def fetch_mapping_by_ids(db: AsyncSession, room_id: int, amenity_id: int):
    """Fetch amenity mapping by room_id and amenity_id (deprecated - kept for compatibility)"""
    # This is a stub for compatibility - mapping is now at room_type level
    # Get the room's type and check if the amenity is mapped to that type
    room = await fetch_room_by_id(db, room_id)
    if not room:
        return None
    
    res = await db.execute(
        select(RoomTypeAmenityMap)
        .where(RoomTypeAmenityMap.room_type_id == room.room_type_id)
        .where(RoomTypeAmenityMap.amenity_id == amenity_id)
    )
    return res.scalars().first()


async def delete_room_amenity_map(db: AsyncSession, mapping_record) -> None:
    """Delete an amenity mapping (deprecated - uses room_type level now)"""
    if mapping_record:
        await db.delete(mapping_record)
        await db.flush()


async def fetch_mapping_exists(db: AsyncSession, room_id: int, amenity_id: int):
    """Check if amenity mapping exists for room (deprecated - compatibility only)"""
    room = await fetch_room_by_id(db, room_id)
    if not room:
        return None
    
    res = await db.execute(
        select(RoomTypeAmenityMap)
        .where(RoomTypeAmenityMap.room_type_id == room.room_type_id)
        .where(RoomTypeAmenityMap.amenity_id == amenity_id)
    )
    return res.scalars().first()


async def insert_room_amenity_map(db: AsyncSession, data: dict):
    """Insert room-amenity mapping (deprecated - maps to room-type level now)"""
    # This is a stub for compatibility - when called with room_id, we map at room-type level
    if 'room_id' in data:
        room = await fetch_room_by_id(db, data['room_id'])
        if not room:
            return None
        
        # Check if already mapped at room-type level
        existing = await db.execute(
            select(RoomTypeAmenityMap)
            .where(RoomTypeAmenityMap.room_type_id == room.room_type_id)
            .where(RoomTypeAmenityMap.amenity_id == data['amenity_id'])
        )
        
        if existing.scalars().first():
            return existing.scalars().first()
        
        # Create mapping at room-type level
        mapping = RoomTypeAmenityMap(
            room_type_id=room.room_type_id,
            amenity_id=data['amenity_id']
        )
        db.add(mapping)
        await db.flush()
        return mapping
    
    return None


async def fetch_amenities_by_room_id(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
    """Get amenities for a specific room (through room type)"""
    res = await db.execute(
        select(RoomAmenities)
        .join(RoomTypeAmenityMap, RoomTypeAmenityMap.amenity_id == RoomAmenities.amenity_id)
        .join(RoomTypes, RoomTypes.room_type_id == RoomTypeAmenityMap.room_type_id)
        .join(Rooms, Rooms.room_type_id == RoomTypes.room_type_id)
        .where(Rooms.room_id == room_id)
    )
    return res.scalars().all()
