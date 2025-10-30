import httpx
from fastapi import UploadFile
from uuid import uuid4

EXTERNAL_API = "https://image-upload-backend-v12y.onrender.com/upload"

async def save_uploaded_image(image: UploadFile, image_name: str) -> str:
    """
    Sends image to external upload API and returns the hosted URL.
    """
    unique_name = f"{image_name}_{uuid4().hex}"
    form_data = {
        "image_name": unique_name,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
        files = {"image": (image.filename, await image.read(), image.content_type)}
        response = await client.post(EXTERNAL_API, data=form_data, files=files)
    if response.status_code != 200:
        raise Exception(f"External upload failed: {response.text}")

    return response.json().get("url")
