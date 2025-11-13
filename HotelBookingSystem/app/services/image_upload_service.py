import os
import time
import asyncio
from uuid import uuid4

import httpx
from fastapi import UploadFile
from cloudinary import uploader
from app.utils.cloudinary_image_util import upload_image_to_cloudinary
# Primary external upload endpoint; can be overridden with env var IMAGE_UPLOAD_API


async def save_uploaded_image(_image: UploadFile) -> str:
    image=await _image.read()

    result=await upload_image_to_cloudinary(image)
    return result['url']