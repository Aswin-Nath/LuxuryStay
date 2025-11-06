from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BackupRestoreDetails(BaseModel):
    # Arbitrary metadata for the event (e.g., compression, restoreMode, checksumVerified)
    details: Optional[Dict[str, Any]] = None


class BackupRestoreLog(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    type: str = Field(..., description="Defines log category: 'backup' or 'restore'")
    message: Optional[str] = Field(None, description="Descriptive event or task message")
    status: Optional[str] = Field(None, description="Log outcome: info, success, warning, error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event creation time in UTC")
    durationMs: Optional[int] = None
    triggeredBy: Optional[str] = None
    node: Optional[str] = None
    errorDetails: Optional[Dict[str, Any]] = None
    backupRefId: Optional[str] = None
    restoreRefId: Optional[str] = None
    targetDatabase: Optional[str] = None
    validated: Optional[bool] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "type": "backup",
                "message": "Backup completed",
                "status": "success",
                "timestamp": "2025-11-06T00:00:00Z",
                "durationMs": 1500000,
                "triggeredBy": "system",
                "node": "node-1",
                "backupRefId": "653a4f...",
                "details": {"compression": "gzip", "checksumVerified": True},
            }
        }
