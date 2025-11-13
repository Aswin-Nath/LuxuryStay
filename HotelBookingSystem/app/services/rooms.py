from typing import List, Optional, Dict, Any
from io import BytesIO
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


from app.models.sqlalchemy_schemas.rooms import (
    Rooms,
    RoomTypes,
    RoomAmenities,
    RoomAmenityMap,
)


from app.crud.rooms import (
    # Room Type CRUD
    insert_room_type,
    fetch_room_type_by_name,
    fetch_all_room_types,
    fetch_room_type_by_id,
    update_room_type_by_id,
    mark_room_type_deleted,

    # Room CRUD
    insert_room,
    fetch_room_by_id,
    fetch_room_by_number,
    fetch_rooms_filtered,
    update_room_by_id,
    soft_delete_room,

    # Amenity CRUD
    insert_amenity,
    fetch_all_amenities,
    fetch_amenity_by_id,
    fetch_amenity_by_name,
    remove_amenity,

    # Room-Amenity Mapping CRUD
    fetch_mapping_exists,
    insert_room_amenity_map,
    fetch_amenities_by_room_id,
    fetch_rooms_by_amenity_id,
    fetch_mapping_by_ids,
    delete_room_amenity_map,
)

# ==========================================================
# 🔹 CREATE ROOM TYPE
# ==========================================================
async def create_room_type(db: AsyncSession, payload) -> RoomTypes:
	existing_type = await fetch_room_type_by_name(db, payload.type_name)
	if existing_type:
		raise HTTPException(status_code=409, detail="Room type already exists")

	room_type_record = await insert_room_type(db, payload.model_dump())
	await db.commit()
	await db.refresh(room_type_record)
	return room_type_record


# ==========================================================
# 🔹 LIST ROOM TYPES
# ==========================================================
async def list_room_types(db: AsyncSession, include_deleted: Optional[bool] = False) -> List[RoomTypes]:
	return await fetch_all_room_types(db, include_deleted)


# ==========================================================
# 🔹 GET ROOM TYPE
# ==========================================================
async def get_room_type(db: AsyncSession, room_type_id: int) -> RoomTypes:
	room_type_record = await fetch_room_type_by_id(db, room_type_id)
	if not room_type_record:
		raise HTTPException(status_code=404, detail="Room type not found")
	return room_type_record


# ==========================================================
# 🔹 UPDATE ROOM TYPE
# ==========================================================
async def update_room_type(db: AsyncSession, room_type_id: int, payload) -> RoomTypes:
	room_type_record = await fetch_room_type_by_id(db, room_type_id)
	if not room_type_record:
		raise HTTPException(status_code=404, detail="Room type not found")

	room_type_data = payload.model_dump(exclude_unset=True)
	await update_room_type_by_id(db, room_type_id, room_type_data)
	await db.commit()

	room_type_record = await fetch_room_type_by_id(db, room_type_id)
	return room_type_record


# ==========================================================
# 🔹 SOFT DELETE ROOM TYPE
# ==========================================================
async def soft_delete_room_type(db: AsyncSession, room_type_id: int) -> None:
	room_type_record = await fetch_room_type_by_id(db, room_type_id)
	if not room_type_record:
		raise HTTPException(status_code=404, detail="Room type not found")

	await mark_room_type_deleted(db, room_type_id)
	await db.commit()


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



# ==========================================================
# 🔹 MAP AMENITY TO ROOM
# ==========================================================
async def map_amenity(db: AsyncSession, payload) -> None:
	room_record = await fetch_room_by_id(db, payload.room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	amenity_record = await fetch_amenity_by_id(db, payload.amenity_id)
	if not amenity_record:
		raise HTTPException(status_code=404, detail="Amenity not found")

	existing_mapping = await fetch_mapping_exists(db, payload.room_id, payload.amenity_id)
	if existing_mapping:
		raise HTTPException(status_code=409, detail="Mapping already exists")

	amenity_mapping = await insert_room_amenity_map(db, payload.model_dump())
	await db.commit()
	return amenity_mapping


# ==========================================================
# 🔹 GET AMENITIES FOR A ROOM
# ==========================================================
async def get_amenities_for_room(db: AsyncSession, room_id: int) -> List[RoomAmenities]:
	return await fetch_amenities_by_room_id(db, room_id)


# ==========================================================
# 🔹 GET ROOMS FOR AN AMENITY
# ==========================================================
async def get_rooms_for_amenity(db: AsyncSession, amenity_id: int) -> List[Rooms]:
	return await fetch_rooms_by_amenity_id(db, amenity_id)


# ==========================================================
# 🔹 UNMAP AMENITY FROM ROOM
# ==========================================================
async def unmap_amenity(db: AsyncSession, room_id: int, amenity_id: int) -> None:
	amenity_mapping = await fetch_mapping_by_ids(db, room_id, amenity_id)
	if not amenity_mapping:
		raise HTTPException(status_code=404, detail="Mapping not found")

	await delete_room_amenity_map(db, amenity_mapping)
	await db.commit()


# ==========================================================
# 🔹 MAP MULTIPLE AMENITIES TO ROOM (BULK)
# ==========================================================
async def map_amenities_bulk(db: AsyncSession, room_id: int, amenity_ids: List[int]) -> dict:
	"""
	Map multiple amenities to a room.
	Returns a summary of successfully mapped, already existing, and failed mappings.
	"""
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	result = {
		"room_id": room_id,
		"successfully_mapped": [],
		"already_existed": [],
		"failed": []
	}

	for amenity_id in amenity_ids:
		try:
			# Check if amenity exists
			amenity_record = await fetch_amenity_by_id(db, amenity_id)
			if not amenity_record:
				result["failed"].append({
					"amenity_id": amenity_id,
					"reason": "Amenity not found"
				})
				continue

			# Check if mapping already exists
			existing_mapping = await fetch_mapping_exists(db, room_id, amenity_id)
			if existing_mapping:
				result["already_existed"].append(amenity_id)
				continue

			# Create the mapping
			await insert_room_amenity_map(db, {"room_id": room_id, "amenity_id": amenity_id})
			result["successfully_mapped"].append(amenity_id)

		except Exception as e:
			result["failed"].append({
				"amenity_id": amenity_id,
				"reason": str(e)
			})

	await db.commit()
	return result


# ==========================================================
# 🔹 UNMAP MULTIPLE AMENITIES FROM ROOM (BULK)
# ==========================================================
async def unmap_amenities_bulk(db: AsyncSession, room_id: int, amenity_ids: List[int]) -> dict:
	"""
	Unmap multiple amenities from a room.
	Returns a summary of successfully unmapped, not found, and failed unmappings.
	"""
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	result = {
		"room_id": room_id,
		"successfully_unmapped": [],
		"not_found": [],
		"failed": []
	}

	for amenity_id in amenity_ids:
		try:
			amenity_mapping = await fetch_mapping_by_ids(db, room_id, amenity_id)
			if not amenity_mapping:
				result["not_found"].append(amenity_id)
				continue

			await delete_room_amenity_map(db, amenity_mapping)
			result["successfully_unmapped"].append(amenity_id)

		except Exception as e:
			result["failed"].append({
				"amenity_id": amenity_id,
				"reason": str(e)
			})

	await db.commit()
	return result



# ==========================================================
# 🔹 CREATE AMENITY
# ==========================================================
async def create_amenity(db: AsyncSession, payload) -> RoomAmenities:
	existing_amenity = await fetch_amenity_by_name(db, payload.amenity_name)
	if existing_amenity:
		raise HTTPException(status_code=409, detail="Amenity already exists")

	amenity_record = await insert_amenity(db, payload.model_dump())
	await db.commit()
	await db.refresh(amenity_record)
	return amenity_record


# ==========================================================
# 🔹 LIST AMENITIES
# ==========================================================
async def list_amenities(db: AsyncSession) -> List[RoomAmenities]:
	return await fetch_all_amenities(db)


# ==========================================================
# 🔹 GET AMENITY
# ==========================================================
async def get_amenity(db: AsyncSession, amenity_id: int) -> RoomAmenities:
	amenity_record = await fetch_amenity_by_id(db, amenity_id)
	if not amenity_record:
		raise HTTPException(status_code=404, detail="Amenity not found")
	return amenity_record


# ==========================================================
# 🔹 DELETE AMENITY
# ==========================================================
async def delete_amenity(db: AsyncSession, amenity_id: int) -> None:
	amenity_record = await fetch_amenity_by_id(db, amenity_id)
	if not amenity_record:
		raise HTTPException(status_code=404, detail="Amenity not found")

	# check if amenity is mapped to any rooms using a COUNT query
	mapped_count = await db.execute(
		select(func.count()).select_from(RoomAmenityMap).where(RoomAmenityMap.amenity_id == amenity_id)
	)
	count_result = mapped_count.scalar()
	if count_result > 0:
		raise HTTPException(status_code=400, detail="Amenity is mapped to rooms; unmap first")

	await remove_amenity(db, amenity_record)
	await db.commit()
