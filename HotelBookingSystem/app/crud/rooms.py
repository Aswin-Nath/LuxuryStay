from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# ==========================================================
# 🧱 MODELS
# ==========================================================
from app.models.sqlalchemy_schemas.rooms import (
    Rooms,
    RoomTypes,
    RoomAmenities,
    RoomAmenityMap,
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


async def fetch_all_room_types(db: AsyncSession, include_deleted: bool = False) -> List[RoomTypes]:
    stmt = select(RoomTypes)
    if not include_deleted:
        stmt = stmt.where(RoomTypes.is_deleted.is_(False))
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


# ==========================================================
# 🔹 ROOM-AMENITY MAP CRUD
# ==========================================================
async def insert_room_amenity_map(db: AsyncSession, data: dict) -> RoomAmenityMap:
    record = RoomAmenityMap(**data)
    db.add(record)
    await db.flush()
    return record


async def fetch_mapping_exists(db: AsyncSession, room_id: int, amenity_id: int) -> Optional[RoomAmenityMap]:
    res = await db.execute(
        select(RoomAmenityMap)
        .where(RoomAmenityMap.room_id == room_id)
        .where(RoomAmenityMap.amenity_id == amenity_id)
    )
    return res.scalars().first()


async def fetch_mapping_by_ids(db: AsyncSession, room_id: int, amenity_id: int) -> Optional[RoomAmenityMap]:
    res = await db.execute(
        select(RoomAmenityMap)
        .where(RoomAmenityMap.room_id == room_id)
        .where(RoomAmenityMap.amenity_id == amenity_id)
    )
    return res.scalars().first()


async def fetch_amenities_by_room_id(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
    res = await db.execute(
        select(RoomAmenities)
        .join(RoomAmenityMap, RoomAmenityMap.amenity_id == RoomAmenities.amenity_id)
        .where(RoomAmenityMap.room_id == room_id)
    )
    return res.scalars().all()


async def fetch_rooms_by_amenity_id(db: AsyncSession, amenity_id: int) -> List[Rooms]:
    res = await db.execute(
        select(Rooms)
        .join(RoomAmenityMap, RoomAmenityMap.room_id == Rooms.room_id)
        .where(RoomAmenityMap.amenity_id == amenity_id)
    )
    return res.scalars().all()


async def delete_room_amenity_map(db: AsyncSession, mapping_record: RoomAmenityMap) -> None:
    await db.delete(mapping_record)
    await db.flush()
