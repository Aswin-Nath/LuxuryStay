from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.images import Images
from app.models.sqlalchemy_schemas.rooms import Rooms


async def create_image(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: int,
    image_url: str,
    caption: Optional[str] = None,
    is_primary: bool = False,
    uploaded_by: Optional[int] = None,
) -> Images:
    # If the image is for a room, ensure room exists
    if entity_type == "room":
        res = await db.execute(select(Rooms).where(Rooms.room_id == entity_id))
        room = res.scalars().first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # If this image is primary, unset other primary images for the same entity
    if is_primary:
        await db.execute(
            update(Images)
            .where(Images.entity_type == entity_type)
            .where(Images.entity_id == entity_id)
            .values(is_primary=False)
        )

    data = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "image_url": image_url,
        "caption": caption,
        "is_primary": is_primary,
        "uploaded_by": uploaded_by,
    }

    obj = Images(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_images_for_room(db: AsyncSession, room_id: int) -> List[Images]:
    stmt = select(Images).where(Images.entity_type == "room").where(Images.entity_id == room_id).where(Images.is_deleted == False)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items
