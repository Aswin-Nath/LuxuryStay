from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes

from app.models.sqlalchemy_schemas.images import Images
from app.models.sqlalchemy_schemas.rooms import RoomTypes
from app.models.sqlalchemy_schemas.reviews import Reviews
from app.models.sqlalchemy_schemas.issues import Issues

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
    # We maintain images at the room-type level (centralized). Accept either
    # entity_type == "room_type" or legacy "room" and treat both as room-type images.
    effective_entity_type = entity_type

    # Validate entity existence depending on entity_type
    if effective_entity_type == "room_type":
        res = await db.execute(select(RoomTypes).where(RoomTypes.room_type_id == entity_id))
        room_type = res.scalars().first()
        if not room_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    elif effective_entity_type == "review":
        # ensure review exists
        res = await db.execute(select(Reviews).where(Reviews.review_id == entity_id))
        review = res.scalars().first()
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    elif effective_entity_type=="issue":
        res=await db.execute(select(Issues).where(Issues.issue_id==entity_id))
        issue=res.scalars().first()
        if not issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # If this image is primary, unset other primary images for the same entity
    if is_primary:
        # unset other primary images for the effective entity type (room_type)
        await db.execute(
            update(Images)
            .where(Images.entity_type == effective_entity_type)
            .where(Images.entity_id == entity_id)
            .values(is_primary=False)
        )

    data = {
        "entity_type": effective_entity_type,
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


async def get_images_for_room(db: AsyncSession, room_type_id: int) -> List[Images]:
    """Return images for a given room type (centralized images shown to customers).

    Keep function name for backwards compatibility but the parameter is a room_type_id.
    """
    stmt = (
        select(Images)
        .where(Images.entity_type == "room_type")
        .where(Images.entity_id == room_type_id)
        .where(Images.is_deleted == False)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def get_images_for_review(db: AsyncSession, review_id: int) -> List[Images]:
    """Return images attached to a review."""
    stmt = (
        select(Images)
        .where(Images.entity_type == "review")
        .where(Images.entity_id == review_id)
        .where(Images.is_deleted == False)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def get_images_for_entity(db: AsyncSession, entity_type: str, entity_id: int) -> List[Images]:
    """Generic getter for images for any entity type (room_type, review, issue, etc.)."""
    stmt = (
        select(Images)
        .where(Images.entity_type == entity_type)
        .where(Images.entity_id == entity_id)
        .where(Images.is_deleted == False)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


async def hard_delete_image(db: AsyncSession, image_id: int, requester_id: int | None = None, requester_permissions: dict | None = None) -> None:
    """Permanently delete an image row. Only the uploader or users with room_service.WRITE may delete.

    This removes the DB row; it does NOT attempt to delete remote file contents (external upload providers may
    require separate deletion APIs).
    """
    q = await db.execute(select(Images).where(Images.image_id == image_id))
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # If it's a room/room_type image, requester must either be uploader or have room_service.WRITE
    allowed = False
    if requester_id and obj.uploaded_by and requester_id == obj.uploaded_by:
        allowed = True
    if requester_permissions:
        if (
            Resources.ROOM_MANAGEMENT.value in requester_permissions
            and PermissionTypes.WRITE.value in requester_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
        ):
            allowed = True
    # Allow review owner to delete images attached to their review
    if not allowed and obj.entity_type == "review" and requester_id:
        res = await db.execute(select(Reviews).where(Reviews.review_id == obj.entity_id))
        review = res.scalars().first()
        if review and review.user_id == requester_id:
            allowed = True

    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to delete image")

    # Permanently delete the DB row
    await db.delete(obj)
    await db.commit()


async def set_image_primary(db: AsyncSession, image_id: int, requester_id: int | None = None, requester_permissions: dict | None = None) -> None:
    """Mark the given image as primary for its entity (unset others).

    Only uploader or users with ROOM_MANAGEMENT.WRITE may perform this.
    """
    q = await db.execute(select(Images).where(Images.image_id == image_id))
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Permission check: uploader or ROOM_MANAGEMENT.WRITE
    allowed = False
    if requester_id and obj.uploaded_by and requester_id == obj.uploaded_by:
        allowed = True
    if requester_permissions:
        if (
            Resources.ROOM_MANAGEMENT.value in requester_permissions
            and PermissionTypes.WRITE.value in requester_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
        ):
            allowed = True

    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to set primary image")

    # Unset other primary images for same entity
    await db.execute(
        update(Images)
        .where(Images.entity_type == obj.entity_type)
        .where(Images.entity_id == obj.entity_id)
        .values(is_primary=False)
    )

    # Set this image primary
    obj.is_primary = True
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return None
