from typing import Optional, List, Literal
from datetime import datetime, timezone
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
    type: Literal["announcement", "banner", "testimonial", "promotion"]
    title: str
    description: str
    media: Media
    status: Literal["used", "unused", "draft", "published"] = "used"
    metadata: Optional[Metadata] = None
    images: Optional[List[Image]] = []
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    
