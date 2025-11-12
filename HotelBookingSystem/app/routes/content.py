from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Form, File, UploadFile,Security
from motor.motor_asyncio import AsyncIOMotorClient
import json
from app.dependencies.authentication import check_permission
from app.services.content_service import (
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


# ============================================================================
# 🔹 CREATE - Create a new CMS content document with media
# ============================================================================
@router.post("/", response_model=dict)
async def create_content_doc(
    type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    status: Optional[str] = Form("used"),
    metadata: Optional[str] = Form(None),
    media: UploadFile = File(...),
    images: Optional[List[UploadFile]] = File(default=[]),
    collection=Depends(get_collection),
    token_payload: dict = Security(check_permission, scopes=["CONTENT_MANAGEMENT:WRITE"])
):
    """
    Create a new CMS content document with media attachments.
    
    Creates a CMS content document with primary media file and optional images. Media files
    are automatically uploaded and stored. Metadata can be provided as JSON string. Document
    starts in the specified status (default: "used").
    
    Args:
        type (str): Content type (e.g., "article", "banner", "guide").
        title (str): Document title.
        description (str): Detailed description of content.
        status (Optional[str]): Document status (default: "used").
        metadata (Optional[str]): JSON string containing additional metadata.
        media (UploadFile): Primary media file for the content.
        images (Optional[List[UploadFile]]): Additional images to attach.
        collection: MongoDB collection dependency.
    
    Returns:
        dict: Created document with _id, file URLs, and metadata.
    
    Raises:
        HTTPException (400): If required fields missing or invalid JSON metadata.
        HTTPException (500): If file upload fails.
    
    Side Effects:
        - Uploads media files to storage.
        - Creates document record in MongoDB.
    """
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


# ============================================================================
# 🔹 READ - Fetch all CMS content documents
# ============================================================================
@router.get("/", response_model=list)
async def get_all_content_docs(collection=Depends(get_collection)):
    """
    Retrieve all CMS content documents.
    
    Fetches all content documents from MongoDB collection with their metadata and file URLs.
    
    Args:
        collection: MongoDB collection dependency.
    
    Returns:
        list: Array of all content documents with details.
    
    Raises:
        HTTPException (500): If database query fails.
    """
    return await get_all_docs_service(collection)


# ============================================================================
# 🔹 READ - Fetch single CMS content document
# ============================================================================
@router.get("/{id}", response_model=dict)
async def get_content_doc(id: str, collection=Depends(get_collection)):
    """
    Retrieve a single CMS content document by ID.
    
    Fetches a specific content document from MongoDB using its ObjectId.
    
    Args:
        id (str): MongoDB ObjectId of the content document.
        collection: MongoDB collection dependency.
    
    Returns:
        dict: Content document with all details and file URLs.
    
    Raises:
        HTTPException (404): If document not found.
        HTTPException (500): If database query fails.
    """
    return await get_doc_service(collection, id)


# ============================================================================
# 🔹 UPDATE - Modify CMS content document details
# ============================================================================
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
    token_payload: dict = Security(check_permission, scopes=["CONTENT_MANAGEMENT:WRITE"])
):
    """
    Update CMS content document details and media.
    
    Modifies existing content document. Supports partial updates - only provided fields are updated.
    New media files replace old ones.
    
    Args:
        id (str): MongoDB ObjectId of the document to update.
        title (Optional[str]): New document title.
        description (Optional[str]): New document description.
        status (Optional[str]): New document status.
        metadata (Optional[str]): New metadata as JSON string.
        new_media (Optional[UploadFile]): Replacement media file.
        new_images (Optional[List[UploadFile]]): Replacement images.
        collection: MongoDB collection dependency.
    
    Returns:
        dict: Updated content document.
    
    Raises:
        HTTPException (400): If invalid JSON metadata.
        HTTPException (404): If document not found.
        HTTPException (500): If update fails.
    
    Side Effects:
        - Uploads new media files if provided.
        - Removes old media files.
        - Updates document in MongoDB.
    """
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


# ============================================================================
# 🔹 DELETE - Remove CMS content document
# ============================================================================
@router.delete("/{id}", response_model=dict)
async def delete_content_doc(id: str, collection=Depends(get_collection), token_payload: dict = Security(check_permission, scopes=["CONTENT_MANAGEMENT:WRITE"])):
    """
    Delete/remove CMS content document.
    
    Soft or hard deletes a content document and its associated media files.
    
    Args:
        id (str): MongoDB ObjectId of the document to delete.
        collection: MongoDB collection dependency.
    
    Returns:
        dict: Confirmation message with deleted document details.
    
    Raises:
        HTTPException (404): If document not found.
        HTTPException (500): If deletion fails.
    
    Side Effects:
        - Deletes document from MongoDB.
        - Removes associated media files from storage.
    """
    return await delete_doc_service(collection, id)
