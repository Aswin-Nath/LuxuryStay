from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Media(BaseModel):
    url: Optional[HttpUrl]
    type: Optional[str] = Field(default="image")


class ImageItem(BaseModel):
    url: Optional[HttpUrl]
    caption: Optional[str] = None


class ContentDocModel(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    type: str = Field(..., description="announcement | banner | offer | testimonial | promotion")
    title: str
    description: Optional[str] = None
    media: Optional[Media] = None
    status: Optional[str] = Field(default="draft", description="used | unused | draft | published")
    metadata: Optional[Dict[str, Any]] = None
    order: Optional[int] = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    images: Optional[List[ImageItem]] = None

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "type": "banner",
                "title": "Spring Sale",
                "description": "Up to 30% off",
                "media": {"url": "https://example.com/banner.jpg", "type": "image"},
                "status": "published",
                "metadata": {"cta": "Book now", "discount": 30},
                "order": 1,
                "images": [{"url": "https://example.com/img1.jpg", "caption": "Main banner"}],
            }
        }
