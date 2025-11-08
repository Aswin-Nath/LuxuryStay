from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Form, File, UploadFile
from motor.motor_asyncio import AsyncIOMotorClient
import json

from app.services.content_management_service.content_service import (
    create_doc_service,
    get_all_docs_service,
    get_doc_service,
    update_doc_service,
    delete_doc_service,
)

router = APIRouter(prefix="/content", tags=["Content"])


# ───────────────────────────────
# MongoDB Collection Dependency
# ───────────────────────────────
async def get_collection():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["hotel_cms"]
    return db["content_docs"]


# ───────────────────────────────
# POST — Create CMS Document
# ───────────────────────────────
@router.post("/", response_model=dict)
async def create_content_doc(
    type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    status: Optional[str] = Form("used"),
    metadata: Optional[str] = Form(None),
    media: UploadFile = File(...),
    images: Optional[List[UploadFile]] = File(None),
    collection=Depends(get_collection),
):
    meta_obj: Optional[Dict[str, Any]] = None
    if metadata:
        try:
            meta_obj = json.loads(metadata)
        except json.JSONDecodeError:
            meta_obj = {}

    return await create_doc_service(
        collection=collection,
        type=type,
        title=title,
        description=description,
        media=media,
        images=images,
        status=status,
        metadata=meta_obj,
    )


# ───────────────────────────────
# GET — All Content Docs
# ───────────────────────────────
@router.get("/", response_model=list)
async def get_all_content_docs(collection=Depends(get_collection)):
    return await get_all_docs_service(collection)


# ───────────────────────────────
# GET — Single Content Doc
# ───────────────────────────────
@router.get("/{id}", response_model=dict)
async def get_content_doc(id: str, collection=Depends(get_collection)):
    return await get_doc_service(collection, id)


# ───────────────────────────────
# PUT — Update Content Doc
# ───────────────────────────────
@router.put("/{id}", response_model=dict)
async def update_content_doc(
    id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    new_media: Optional[UploadFile] = File(None),
    new_images: Optional[List[UploadFile]] = File(None),
    collection=Depends(get_collection),
):
    payload = {}
    if title:
        payload["title"] = title
    if description:
        payload["description"] = description
    if status:
        payload["status"] = status
    if metadata:
        try:
            payload["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            payload["metadata"] = {}

    return await update_doc_service(collection, id, payload, new_media, new_images)


# ───────────────────────────────
# DELETE — Remove Content Doc
# ───────────────────────────────
@router.delete("/{id}", response_model=dict)
async def delete_content_doc(id: str, collection=Depends(get_collection)):
    return await delete_doc_service(collection, id)
