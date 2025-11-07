from typing import List, Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import pandas as pd
from io import BytesIO

from app.models.sqlalchemy_schemas.rooms import Rooms, RoomTypes


async def create_room(db: AsyncSession, payload) -> Rooms:
    # Consider only non-deleted rooms when checking uniqueness of room number.
    q = await db.execute(
        select(Rooms).where(Rooms.room_no == payload.room_no, Rooms.is_deleted.is_(False))
    )
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    # Fetch room type to derive price and occupancy limits
    rt_res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == payload.room_type_id))
    room_type = rt_res.scalars().first()
    if not room_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    # For creation, use full payload (required fields must be present).
    data = payload.model_dump()
    # populate derived fields from room type
    data["price_per_night"] = room_type.price_per_night
    data["max_adult_count"] = room_type.max_adult_count
    data["max_child_count"] = room_type.max_child_count

    obj = Rooms(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_rooms(
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

    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def get_room(db: AsyncSession, room_id: int) -> Rooms:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return obj


async def update_room(db: AsyncSession, room_id: int, payload) -> Rooms:
    q = await db.execute(select(Rooms).where(Rooms.room_no == payload.room_no))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Apply only fields explicitly provided by client to avoid overwriting existing values.
    data = payload.model_dump(exclude_unset=True)
    # If room_type_id changed (or provided), fetch derived values and set them

    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(**data))
    await db.commit()
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    return obj





async def delete_room(db: AsyncSession, room_id: int) -> None:
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    # Soft delete: mark the row as deleted instead of removing it.
    await db.execute(update(Rooms).where(Rooms.room_id == room_id).values(is_deleted=True))
    await db.commit()


async def bulk_upload_rooms(db: AsyncSession, file_content: bytes) -> Dict[str, Any]:
    """
    Bulk upload rooms from an Excel file.
    
    Expected columns in Excel:
    - room_no (required): Room number
    - room_type_id (required): ID of the room type
    - room_status (optional): Room status (AVAILABLE, BOOKED, MAINTENANCE, FROZEN) - defaults to AVAILABLE
    - freeze_reason (optional): Freeze reason (NONE, CLEANING, ADMIN_LOCK, SYSTEM_HOLD) - defaults to NONE
    
    Returns:
    {
        "total_processed": int,
        "successfully_created": int,
        "skipped": int,
        "created_rooms": [{"room_no": "...", "room_id": ..., "room_type_id": ...}, ...],
        "skipped_rooms": [{"room_no": "...", "reason": "..."}, ...]
    }
    """
    try:
        # Read Excel file into DataFrame
        df = pd.read_excel(BytesIO(file_content))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read Excel file: {str(e)}")
    
    # Validate required columns exist
    required_columns = {"room_no", "room_type_id"}
    if not required_columns.issubset(df.columns):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Excel must contain columns: {', '.join(required_columns)}"
        )
    
    created_rooms: List[Dict[str, Any]] = []
    skipped_rooms: List[Dict[str, str]] = []
    
    for idx, row in df.iterrows():
        try:
            room_no = str(row["room_no"]).strip()
            room_type_id = int(row["room_type_id"])
            room_status = str(row.get("room_status", "AVAILABLE")).strip().upper()
            freeze_reason = str(row.get("freeze_reason", "NONE")).strip().upper()
            
            # Validate room_no is not empty
            if not room_no:
                skipped_rooms.append({
                    "room_no": f"Row {idx + 2}",  # +2 because Excel is 1-indexed and has header
                    "reason": "Room number is empty"
                })
                continue
            
            # Check if room already exists
            q = await db.execute(
                select(Rooms).where(Rooms.room_no == room_no, Rooms.is_deleted.is_(False))
            )
            if q.scalars().first():
                skipped_rooms.append({
                    "room_no": room_no,
                    "reason": "Room number already exists"
                })
                continue
            
            # Validate room_type_id exists
            rt_res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == room_type_id))
            room_type = rt_res.scalars().first()
            if not room_type:
                skipped_rooms.append({
                    "room_no": room_no,
                    "reason": f"Room type ID {room_type_id} not found"
                })
                continue
            
            # Validate room_status enum value
            valid_statuses = ["AVAILABLE", "BOOKED", "MAINTENANCE", "FROZEN"]
            if room_status not in valid_statuses:
                skipped_rooms.append({
                    "room_no": room_no,
                    "reason": f"Invalid room_status '{room_status}'. Must be one of: {', '.join(valid_statuses)}"
                })
                continue
            
            # Validate freeze_reason enum value
            valid_freeze_reasons = ["NONE", "CLEANING", "ADMIN_LOCK", "SYSTEM_HOLD"]
            if freeze_reason not in valid_freeze_reasons:
                skipped_rooms.append({
                    "room_no": room_no,
                    "reason": f"Invalid freeze_reason '{freeze_reason}'. Must be one of: {', '.join(valid_freeze_reasons)}"
                })
                continue
            
            # Create the room
            new_room = Rooms(
                room_no=room_no,
                room_type_id=room_type_id,
                room_status=room_status,
                freeze_reason=freeze_reason,
                price_per_night=room_type.price_per_night,
                max_adult_count=room_type.max_adult_count,
                max_child_count=room_type.max_child_count
            )
            
            db.add(new_room)
            await db.flush()  # Flush to get the auto-generated room_id
            
            created_rooms.append({
                "room_no": room_no,
                "room_id": new_room.room_id,
                "room_type_id": room_type_id
            })
            
        except ValueError as e:
            skipped_rooms.append({
                "room_no": str(row.get("room_no", f"Row {idx + 2}")),
                "reason": f"Data type error: {str(e)}"
            })
            continue
        except Exception as e:
            skipped_rooms.append({
                "room_no": str(row.get("room_no", f"Row {idx + 2}")),
                "reason": f"Unexpected error: {str(e)}"
            })
            continue
    
    # Commit all successfully created rooms at once
    await db.commit()
    
    return {
        "total_processed": len(df),
        "successfully_created": len(created_rooms),
        "skipped": len(skipped_rooms),
        "created_rooms": created_rooms,
        "skipped_rooms": skipped_rooms
    }
