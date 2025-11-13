from app.core.cloudinary import cloudinary_client

async def upload_image_to_cloudinary(file_bytes: bytes):
    upload_res = cloudinary_client.uploader.upload(
        file_bytes,
        folder="fastapi_uploads",
        resource_type="image"
    )
    return {
        "url": upload_res["secure_url"],
        "public_id": upload_res["public_id"]
    }
