from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.rooms import Rooms


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_room(db: AsyncSession, data: dict) -> Rooms:
	room_record = Rooms(**data)
	db.add(room_record)
	await db.flush()
	return room_record


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
	query_result = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
	return query_result.scalars().first()


async def fetch_room_by_number(db: AsyncSession, room_no: str, include_deleted: bool = False) -> Optional[Rooms]:
	stmt = select(Rooms).where(Rooms.room_no == room_no)
	if not include_deleted:
		stmt = stmt.where(Rooms.is_deleted.is_(False))
	query_result = await db.execute(stmt)
	return query_result.scalars().first()


async def fetch_rooms_filtered(
	db: AsyncSession,
	room_type_id: Optional[int] = None,
	status_filter: Optional[str] = None,
	is_freezed: Optional[bool] = None,
) -> List[Rooms]:
	stmt = select(Rooms)
	if room_type_id is not None:
		stmt = stmt.where(Rooms.room_type_id == room_type_id)
	if status_filter is not None:
		stmt = stmt.where(Rooms.room_status == status_filter)
	if is_freezed is not None:
		if is_freezed:
			stmt = stmt.where(Rooms.freeze_reason.isnot(None))
		else:
			stmt = stmt.where(Rooms.freeze_reason.is_(None))

	query_result = await db.execute(stmt)
	return query_result.scalars().all()


# ==========================================================
# 🔹 UPDATE
# ==========================================================
async def update_room_by_id(db: AsyncSession, room_id: int, updates: dict) -> None:
	if updates:
		await db.execute(
			update(Rooms)
			.where(Rooms.room_id == room_id)
			.values(**updates)
		)
	await db.flush()


# ==========================================================
# 🔹 DELETE (SOFT)
# ==========================================================
async def soft_delete_room(db: AsyncSession, room_id: int) -> None:
	await db.execute(
		update(Rooms)
		.where(Rooms.room_id == room_id)
		.values(is_deleted=True)
	)
	await db.flush()
