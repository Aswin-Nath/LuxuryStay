from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class Media(BaseModel):
    url: str
    type: Literal["image"] = "image"


class Image(BaseModel):
    url: str  # only URL now — no caption


class Metadata(BaseModel):
    CTA: Optional[str] = None
    discount_percent: Optional[float] = None


class ContentDoc(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    type: Literal["announcement", "banner", "offer", "testimonial", "promotion"]
    title: str
    description: str
    media: Media
    status: Literal["used", "unused", "draft", "published"] = "used"
    metadata: Optional[Metadata] = None
    images: Optional[List[Image]] = []
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "offer",
                "title": "Diwali Fest Offer",
                "description": "Celebrate with 20% off on all premium rooms.",
                "media": {"url": "https://cdn.hotel.com/diwali.jpg", "type": "image"},
                "status": "used",
                "metadata": {"CTA": "Book Now", "discount_percent": 20.0},
                "images": [
                    {"url": "https://cdn.hotel.com/img1.jpg"},
                    {"url": "https://cdn.hotel.com/img2.jpg"}
                ],
                "createdAt": "2025-11-08T18:30:00Z",
                "updatedAt": "2025-11-08T18:30:00Z"
            }
        }
    }
