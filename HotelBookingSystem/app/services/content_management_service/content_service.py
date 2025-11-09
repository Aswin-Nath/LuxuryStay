from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status, UploadFile
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Dict, Any, Optional

from app.schemas.pydantic_models.content_docs import ContentDoc
from app.services.images_service.image_upload_service import save_uploaded_image


# ───────────────────────────────
# CREATE
# ───────────────────────────────
async def create_doc_service(
    collection: AsyncIOMotorCollection,
    type: str,
    title: str,
    description: str,
    media: UploadFile,
    images: Optional[List[UploadFile]] = None,
    status: str = "used",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Create a new CMS content document and upload all image assets."""
    media_url = await save_uploaded_image(media)

    image_urls = []
    if images:
        for img in images:
            img_url = await save_uploaded_image(img)
            image_urls.append({"url": img_url})

    payload = ContentDoc(
        type=type,
        title=title,
        description=description,
        media={"url": media_url, "type": "image"},
        status=status,
        metadata=metadata or {},
        images=image_urls,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow(),
    )

    doc = payload.model_dump(by_alias=True)
    doc.pop("_id",None)
    result = await collection.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


# ───────────────────────────────
# READ — ALL & ONE
# ───────────────────────────────
async def get_all_docs_service(collection: AsyncIOMotorCollection):
    cursor = collection.find({})
    documents = await cursor.to_list(length=None)
    for document in documents:
        document["_id"] = str(document["_id"])
    return documents


async def get_doc_service(collection: AsyncIOMotorCollection, id: str):
    content_document = await collection.find_one({"_id": ObjectId(id)})
    if not content_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    content_document["_id"] = str(content_document["_id"])
    return content_document


# ───────────────────────────────
# UPDATE
# ───────────────────────────────
async def update_doc_service(
    collection: AsyncIOMotorCollection,
    id: str,
    payload: Dict[str, Any],
    new_media: Optional[UploadFile] = None,
    new_images: Optional[List[UploadFile]] = None,
):
    update_data = dict(payload)
    update_data["updatedAt"] = datetime.utcnow()

    if new_media:
        update_data["media"] = {"url": await save_uploaded_image(new_media), "type": "image"}

    if new_images:
        image_urls = []
        for image_file in new_images:
            img_url = await save_uploaded_image(image_file)
            image_urls.append({"url": img_url})
        update_data["images"] = image_urls

    result = await collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    return await get_doc_service(collection, id)


# ───────────────────────────────
# DELETE
# ───────────────────────────────
async def delete_doc_service(collection: AsyncIOMotorCollection, id: str):
    result = await collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return {"status": "deleted", "_id": id}
