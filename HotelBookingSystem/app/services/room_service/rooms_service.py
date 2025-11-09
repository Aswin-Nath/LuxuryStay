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
	return await fetch_rooms_filtered(db, room_type_id, status_filter, is_freezed)


# ==========================================================
# 🔹 GET ROOM
# ==========================================================
async def get_room(db: AsyncSession, room_id: int) -> Rooms:
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")
	return room_record


# ==========================================================
# 🔹 UPDATE ROOM
# ==========================================================
async def update_room(db: AsyncSession, room_id: int, payload) -> Rooms:
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
	room_record = await fetch_room_by_id(db, room_id)
	if not room_record:
		raise HTTPException(status_code=404, detail="Room not found")

	await soft_delete_room(db, room_id)
	await db.commit()


# ==========================================================
# 🔹 BULK UPLOAD ROOMS (EXCEL)
# ==========================================================
async def bulk_upload_rooms(db: AsyncSession, file_content: bytes) -> Dict[str, Any]:
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
