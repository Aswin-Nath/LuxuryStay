from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sqlalchemy_schemas.rooms import Rooms


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_room(db: AsyncSession, data: dict) -> Rooms:
	"""
	Insert a new room record into the database.
	
	Creates a new Rooms instance from the provided data dictionary and adds it to the session.
	The record is flushed but not committed (caller handles commit).
	
	Args:
		db (AsyncSession): The async database session.
		data (dict): Dictionary containing room data (room_no, room_type_id, price_per_night, etc).
	
	Returns:
		Rooms: The newly created room object (not yet persisted until commit).
	"""
	room_record = Rooms(**data)
	db.add(room_record)
	await db.flush()
	return room_record


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_room_by_id(db: AsyncSession, room_id: int) -> Optional[Rooms]:
	"""
	Fetch a room by its ID from the database.
	
	Queries the database for a room with the specified room_id.
	
	Args:
		db (AsyncSession): The async database session.
		room_id (int): The unique identifier of the room.
	
	Returns:
		Optional[Rooms]: The room record if found, None otherwise.
	"""
	query_result = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
	return query_result.scalars().first()


async def fetch_room_by_number(db: AsyncSession, room_no: str, include_deleted: bool = False) -> Optional[Rooms]:
	"""
	Fetch a room by its room number.
	
	Queries the database for a room with the specified room_no. By default, excludes soft-deleted rooms.
	
	Args:
		db (AsyncSession): The async database session.
		room_no (str): The room number (e.g., "101", "102").
		include_deleted (bool): If True, includes soft-deleted rooms; if False (default), excludes them.
	
	Returns:
		Optional[Rooms]: The room record if found, None otherwise.
	"""
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
	"""
	Fetch rooms with optional filters.
	
	Queries the database for rooms, optionally filtered by room type, status, or freeze status.
	If multiple filters are provided, they are combined with AND logic.
	
	Args:
		db (AsyncSession): The async database session.
		room_type_id (Optional[int]): Filter by room type ID.
		status_filter (Optional[str]): Filter by room status (e.g., 'AVAILABLE', 'BOOKED', 'MAINTENANCE', 'FROZEN').
		is_freezed (Optional[bool]): If True, fetch frozen rooms; if False, fetch non-frozen rooms.
	
	Returns:
		List[Rooms]: A list of room records matching all provided filter criteria.
	"""
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
	"""
	Update a room record by its ID.
	
	Updates the room with the specified room_id using the provided updates dictionary.
	Only updates fields that are present in the updates dictionary (partial updates supported).
	
	Args:
		db (AsyncSession): The async database session.
		room_id (int): The unique identifier of the room to update.
		updates (dict): Dictionary containing fields to update (e.g., {'room_status': 'BOOKED', 'price_per_night': 150}).
	
	Returns:
		None
	"""
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
	"""
	Soft-delete a room by marking it as deleted.
	
	Sets the is_deleted flag to True for the specified room. The room remains in the database
	but is excluded from queries that filter out deleted records. This preserves historical data.
	
	Args:
		db (AsyncSession): The async database session.
		room_id (int): The unique identifier of the room to soft-delete.
	
	Returns:
		None
	"""
	await db.execute(
		update(Rooms)
		.where(Rooms.room_id == room_id)
		.values(is_deleted=True)
	)
	await db.flush()
