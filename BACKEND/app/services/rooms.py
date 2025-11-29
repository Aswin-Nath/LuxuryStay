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
    RoomTypeAmenityMap,
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
    fetch_rooms_by_type_id,
    update_room_by_id,
    soft_delete_room,

    # Amenity CRUD
    insert_amenity,
    fetch_all_amenities,
    fetch_amenity_by_id,
    fetch_amenity_by_name,
    remove_amenity,
    update_amenity_by_id,

    # Room Type-Amenity Mapping CRUD
    insert_room_type_amenity_map,
    fetch_amenities_by_room_type_id,
    fetch_room_types_by_amenity_id,
    delete_room_type_amenity_map,
    delete_all_amenities_for_room_type,
    fetch_rooms_by_amenity_id,
    fetch_mapping_by_ids,
    delete_room_amenity_map,
    fetch_mapping_exists,
    insert_room_amenity_map,
    fetch_amenities_by_room_id,
)

# ==========================================================
# 🔹 CREATE ROOM TYPE
# ==========================================================
async def create_room_type(db: AsyncSession, payload) -> RoomTypes:
	existing_type = await fetch_room_type_by_name(db, payload.type_name)
	if existing_type:
		raise HTTPException(status_code=409, detail="Room type already exists")

	# Extract amenities before creating room type (not part of RoomTypes model)
	data = payload.model_dump(exclude={'amenities'})
	amenity_ids = payload.amenities or []
	
	room_type_record = await insert_room_type(db, data)
	await db.commit()
	await db.refresh(room_type_record)
	
	# Map amenities directly to the room type (not to individual rooms)
	if amenity_ids:
		for amenity_id in amenity_ids:
			try:
				await insert_room_type_amenity_map(db, {
					'room_type_id': room_type_record.room_type_id,
					'amenity_id': amenity_id
				})
			except Exception:
				pass  # Silently skip if mapping already exists
		await db.commit()
	
	return room_type_record


# ==========================================================
# 🔹 LIST ROOM TYPES
# ==========================================================
async def list_room_types(db: AsyncSession) -> List[RoomTypes]:
	return await fetch_all_room_types(db)


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
	await db.refresh(room_record, ["room_type"])
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
# 🔹 BULK UPLOAD ROOMS (CSV/EXCEL)
# ==========================================================
async def bulk_upload_rooms(db: AsyncSession, file_content: bytes, filename: str = "") -> Dict[str, Any]:
	"""
	Bulk upload rooms from a CSV or Excel file.
	
	Reads a CSV or Excel file containing room data and creates multiple rooms at once. Validates each row for
	required fields and data integrity. Returns a summary of successfully created rooms and skipped entries.
	
	Supports both room_type_id (integer) and room_type_name (string) columns.
	
	Args:
		db (AsyncSession): The database session for executing queries.
		file_content (bytes): The raw bytes content of the file.
		filename (str): The original filename to detect file type.
	
	Returns:
		Dict[str, Any]: A dictionary containing:
			- total_processed (int): Total number of rows processed.
			- successfully_created (int): Number of rooms successfully created.
			- skipped (int): Number of rooms skipped due to errors.
			- created_rooms (List): Details of created rooms with room_id and room_no.
			- skipped_rooms (List): Details of skipped rooms with reasons.
	
	Raises:
		HTTPException (400): If the file cannot be read or required columns are missing.
	"""
	try:
		# Detect file type from filename or try to read as CSV first, then Excel
		if filename.lower().endswith('.csv'):
			df = pd.read_csv(BytesIO(file_content))
		else:
			# Try Excel first (handles .xlsx, .xls)
			try:
				df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
			except Exception:
				# Fallback to CSV if Excel fails
				df = pd.read_csv(BytesIO(file_content))
	except Exception as e:
		raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

	# Normalize column names: strip whitespace and convert to lowercase
	df.columns = df.columns.str.strip().str.lower()
	
	# Debug: log available columns for troubleshooting
	available_columns = list(df.columns)

	# Check if user uploaded room type data instead of room data
	room_type_indicators = {'price', 'adults capacity', 'children capacity', 'square', 'description', 'amenities', 'occupancy'}
	if any(col in available_columns for col in room_type_indicators) and 'room_no' not in available_columns:
		raise HTTPException(
			status_code=400,
			detail="❌ It looks like you're trying to upload ROOM TYPES, not ROOMS. The Bulk Add feature is for adding individual rooms to existing room types. "
				   "Columns detected: " + ", ".join(available_columns) + ". "
				   "✅ For adding rooms, use this format: room_no, room_type_name, room_status (optional), freeze_reason (optional). "
				   "Example: 101, Deluxe, AVAILABLE, NONE"
		)

	required_columns = {"room_no"}
	if not required_columns.issubset(df.columns):
		raise HTTPException(
			status_code=400,
			detail=f"❌ File must contain 'room_no' column. Available columns: {', '.join(available_columns)}. "
				   f"✅ Expected columns: room_no, room_type_name, room_status (optional), freeze_reason (optional)"
		)

	# Check that at least one of room_type_id or room_type_name exists
	if "room_type_id" not in df.columns and "room_type_name" not in df.columns:
		raise HTTPException(
			status_code=400,
			detail="❌ File must contain either 'room_type_id' or 'room_type_name' column. Available columns: " + ", ".join(available_columns) + ". "
				   "✅ Use room_type_name (e.g., 'Deluxe', 'Standard') - IDs are not supported in bulk uploads."
		)

	created_rooms, skipped_rooms = [], []

	for idx, row in df.iterrows():
		try:
			# Safely get room_no with error handling
			if "room_no" not in row.index:
				skipped_rooms.append({"room_no": f"Row {idx + 2}", "reason": "room_no column not found"})
				continue
			
			room_no = str(row["room_no"]).strip()
			room_status = str(row.get("room_status", "AVAILABLE")).strip().upper()
			freeze_reason = str(row.get("freeze_reason", "NONE")).strip().upper()

			if not room_no or room_no == "nan":
				skipped_rooms.append({"room_no": f"Row {idx + 2}", "reason": "Room number is empty"})
				continue

			# Resolve room_type_id from either room_type_id or room_type_name
			room_type_id = None
			
			if "room_type_id" in df.columns and pd.notna(row.get("room_type_id")):
				try:
					room_type_id = int(row["room_type_id"])
				except (ValueError, TypeError):
					skipped_rooms.append({"room_no": room_no, "reason": "room_type_id must be a valid integer"})
					continue
			
			elif "room_type_name" in df.columns and pd.notna(row.get("room_type_name")):
				room_type_name = str(row["room_type_name"]).strip()
				room_type = await fetch_room_type_by_name(db, room_type_name)
				if not room_type:
					skipped_rooms.append({"room_no": room_no, "reason": f"Room type '{room_type_name}' not found"})
					continue
				room_type_id = room_type.room_type_id
			
			else:
				skipped_rooms.append({"room_no": room_no, "reason": "Must provide either room_type_id or room_type_name"})
				continue

			# Validate room exists
			if await fetch_room_by_number(db, room_no):
				skipped_rooms.append({"room_no": room_no, "reason": "Room number already exists"})
				continue

			# Validate room type exists
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

	# ✅ Delete all room-type-amenity mappings for this amenity (CASCADE should handle this, but explicit delete is safer)
	mappings_result = await db.execute(
		select(RoomTypeAmenityMap).where(RoomTypeAmenityMap.amenity_id == amenity_id)
	)
	mappings = mappings_result.scalars().all()
	
	# Delete each mapping
	for mapping in mappings:
		await db.delete(mapping)
	
	print(f"[DELETE_AMENITY] Deleted {len(mappings)} room-type-amenity mappings for amenity {amenity_id}")

	# Then delete the amenity itself
	await remove_amenity(db, amenity_record)
	await db.commit()
	print(f"[DELETE_AMENITY] Successfully deleted amenity {amenity_id}")


# 🔹 UPDATE AMENITY
# ==========================================================
async def update_amenity(db: AsyncSession, amenity_id: int, payload) -> RoomAmenities:
	amenity_record = await fetch_amenity_by_id(db, amenity_id)
	if not amenity_record:
		raise HTTPException(status_code=404, detail="Amenity not found")

	# Check if new name already exists (if different from current)
	if hasattr(payload, 'amenity_name') and payload.amenity_name != amenity_record.amenity_name:
		existing = await fetch_amenity_by_name(db, payload.amenity_name)
		if existing:
			raise HTTPException(status_code=400, detail="Amenity name already exists")

	updates = {}
	if hasattr(payload, 'amenity_name'):
		updates['amenity_name'] = payload.amenity_name
	
	if updates:
		await update_amenity_by_id(db, amenity_id, updates)
	
	await db.commit()
	return await fetch_amenity_by_id(db, amenity_id)

