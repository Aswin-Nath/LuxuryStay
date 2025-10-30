from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.image_upload_service import save_uploaded_image

image_router = APIRouter(prefix="/image", tags=["Image Upload"])

@image_router.post("/")
async def upload_image(image: UploadFile, image_name: str = Form(...)):
    try:
        image_url = await save_uploaded_image(image, image_name)
        return {"message": "Upload Successful!", "url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
