from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditLogModel(BaseModel):
    entity: str = Field(..., description="Entity name, e.g., 'booking', 'room'")
    entity_id: str = Field(..., description="Canonical record reference (string)")
    action: str = Field(..., description="INSERT | UPDATE | DELETE")
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    changed_by_user_id: Optional[int] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[int] = None

    class Config:
        schema_extra = {
            "example": {
                "entity": "booking",
                "entity_id": "booking:123",
                "action": "UPDATE",
                "old_value": {"status": "pending"},
                "new_value": {"status": "confirmed"},
                "changed_by_user_id": 45,
                "ip_address": "203.0.113.5",
                "created_at": "2025-11-06T00:00:00Z",
                "user_id": 12,
            }
        }
