from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from io import BytesIO

from app.models.sqlalchemy_schemas.rooms import Rooms, RoomTypes
from app.crud.room_management.room import (
	insert_room,
	fetch_room_by_id,
	fetch_room_by_number,
	fetch_rooms_filtered,
	update_room_by_id,
	soft_delete_room,
)
from app.crud.room_management.room_types import fetch_room_type_by_id


# ==========================================================
# 🔹 CREATE ROOM
# ==========================================================
async def create_room(db: AsyncSession, payload) -> Rooms:
	"""
	Create a new room in the system.
	
	Validates that the room number is unique and the room type exists.
	Automatically populates price_per_night and occupancy limits from the room type.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		payload (RoomCreate): Pydantic model containing room creation data (room_no, room_type_id, etc).
	
	Returns:
		Rooms: The newly created room record from the database.
	
	Raises:
		HTTPException (409): If a room with the same room_no already exists.
		HTTPException (404): If the specified room_type_id does not exist.
	"""
	existing_room = await fetch_room_by_number(db, payload.room_no)
	if existing_room:
		raise HTTPException(status_code=409, detail="Room number already exists")

	room_type = await fetch_room_type_by_id(db, payload.room_type_id)
	if not room_type:
		raise HTTPException(status_code=404, detail="Room type not found")

	room_data = payload.model_dump()
	room_data["price_per_night"] = room_type.price_per_night
	room_data["max_adult_count"] = room_type.max_adult_count
	room_data["max_child_count"] = room_type.max_child_count

	room_record = await insert_room(db, room_data)
	await db.commit()
	await db.refresh(room_record)
	return room_record


# ==========================================================
# 🔹 LIST ROOMS
# ==========================================================
async def list_rooms(
	db: AsyncSession,
	room_type_id: Optional[int] = None,
	status_filter: Optional[str] = None,
	is_freezed: Optional[bool] = None,
) -> List[Rooms]:
	"""
	Retrieve a list of rooms with optional filters.
	
	Fetches all rooms from the database, optionally filtered by room type, status, or freeze status.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		room_type_id (Optional[int]): Filter by room type ID. If None, no type filtering is applied.
		status_filter (Optional[str]): Filter by room status (e.g., 'AVAILABLE', 'BOOKED', 'MAINTENANCE'). If None, no status filtering is applied.
		is_freezed (Optional[bool]): Filter by freeze status. If True, returns frozen rooms; if False, returns non-frozen rooms; if None, no freeze filtering applied.
	
	Returns:
		List[Rooms]: A list of room records matching the filter criteria.
	"""
	return await fetch_rooms_filtered(db, room_type_id, status_filter, is_freezed)


# ==========================================================
# 🔹 GET ROOM
# ==========================================================
async def get_room(db: AsyncSession, room_id: int) -> Rooms:
	"""
	Retrieve a single room by its ID.
	
	Fetches a room record from the database using the provided room_id.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		room_id (int): The unique identifier of the room to retrieve.
	
	Returns:
		Rooms: The room record with the specified ID.
	
	Raises:
		HTTPException (404): If no room with the specified room_id is found.
	"""
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")
	return room_record


# ==========================================================
# 🔹 UPDATE ROOM
# ==========================================================
async def update_room(db: AsyncSession, room_id: int, payload) -> Rooms:
	"""
	Update an existing room's information.
	
	Updates the specified room with new data from the payload. Validates that the room_no is still unique
	(unless the room_no belongs to the same room being updated). Only fields provided in the payload are updated.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		room_id (int): The unique identifier of the room to update.
		payload (RoomUpdate): Pydantic model containing the fields to update (partial updates supported).
	
	Returns:
		Rooms: The updated room record from the database.
	
	Raises:
		HTTPException (409): If the new room_no already exists on a different room.
		HTTPException (404): If no room with the specified room_id is found.
	"""
	existing_room = await fetch_room_by_number(db, payload.room_no)
	if existing_room and existing_room.room_id != room_id:
		raise HTTPException(status_code=409, detail="Room number already exists")

	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	room_data = payload.model_dump(exclude_unset=True)
	await update_room_by_id(db, room_id, room_data)
	await db.commit()

	room_record = await fetch_room_by_id(db, room_id)
	return room_record


# ==========================================================
# 🔹 DELETE (SOFT DELETE)
# ==========================================================
async def delete_room(db: AsyncSession, room_id: int) -> None:
	"""
	Soft-delete a room by marking it as deleted.
	
	Performs a soft delete by setting the is_deleted flag to True. The room remains in the database
	but is excluded from normal queries. This preserves historical data and bookings.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		room_id (int): The unique identifier of the room to delete.
	
	Returns:
		None
	
	Raises:
		HTTPException (404): If no room with the specified room_id is found.
	"""
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	await soft_delete_room(db, room_id)
	await db.commit()


# ==========================================================
# 🔹 BULK UPLOAD ROOMS (EXCEL)
# ==========================================================
async def bulk_upload_rooms(db: AsyncSession, file_content: bytes) -> Dict[str, Any]:
	"""
	Bulk upload rooms from an Excel file.
	
	Reads an Excel file containing room data and creates multiple rooms at once. Validates each row for
	required fields and data integrity. Returns a summary of successfully created rooms and skipped entries.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		file_content (bytes): The raw bytes content of the Excel file (.xlsx format).
	
	Returns:
		Dict[str, Any]: A dictionary containing:
			- total_processed (int): Total number of rows processed.
			- successfully_created (int): Number of rooms successfully created.
			- skipped (int): Number of rooms skipped due to errors.
			- created_rooms (List): Details of created rooms with room_id and room_no.
			- skipped_rooms (List): Details of skipped rooms with reasons.
	
	Raises:
		HTTPException (400): If the Excel file cannot be read or required columns are missing.
	"""
	try:
		df = pd.read_excel(BytesIO(file_content))
	except Exception as e:
		raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

	required_columns = {"room_no", "room_type_id"}
	if not required_columns.issubset(df.columns):
		raise HTTPException(
			status_code=400,
			detail=f"Excel must contain columns: {', '.join(required_columns)}"
		)

	created_rooms, skipped_rooms = [], []

	for idx, row in df.iterrows():
		try:
			room_no = str(row["room_no"]).strip()
			room_type_id = int(row["room_type_id"])
			room_status = str(row.get("room_status", "AVAILABLE")).strip().upper()
			freeze_reason = str(row.get("freeze_reason", "NONE")).strip().upper()

			if not room_no:
				skipped_rooms.append({"room_no": f"Row {idx + 2}", "reason": "Room number is empty"})
				continue

			if await fetch_room_by_number(db, room_no):
				skipped_rooms.append({"room_no": room_no, "reason": "Room number already exists"})
				continue

			room_type = await fetch_room_type_by_id(db, room_type_id)
			if not room_type:
				skipped_rooms.append({"room_no": room_no, "reason": f"Room type ID {room_type_id} not found"})
				continue

			valid_statuses = ["AVAILABLE", "BOOKED", "MAINTENANCE", "FROZEN"]
			if room_status not in valid_statuses:
				skipped_rooms.append({
					"room_no": room_no,
					"reason": f"Invalid room_status '{room_status}'. Must be one of: {', '.join(valid_statuses)}"
				})
				continue

			valid_freeze_reasons = ["NONE", "CLEANING", "ADMIN_LOCK", "SYSTEM_HOLD"]
			if freeze_reason not in valid_freeze_reasons:
				skipped_rooms.append({
					"room_no": room_no,
					"reason": f"Invalid freeze_reason '{freeze_reason}'. Must be one of: {', '.join(valid_freeze_reasons)}"
				})
				continue

			room_data = {
				"room_no": room_no,
				"room_type_id": room_type_id,
				"room_status": room_status,
				"freeze_reason": freeze_reason,
				"price_per_night": room_type.price_per_night,
				"max_adult_count": room_type.max_adult_count,
				"max_child_count": room_type.max_child_count,
			}

			new_room = await insert_room(db, room_data)
			created_rooms.append({
				"room_no": room_no,
				"room_id": new_room.room_id,
				"room_type_id": room_type_id
			})

		except Exception as e:
			skipped_rooms.append({
				"room_no": str(row.get("room_no", f"Row {idx + 2}")),
				"reason": f"Error: {str(e)}"
			})
			continue

	await db.commit()

	return {
		"total_processed": len(df),
		"successfully_created": len(created_rooms),
		"skipped": len(skipped_rooms),
		"created_rooms": created_rooms,
		"skipped_rooms": skipped_rooms,
	}
