from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RestoreDetails(BaseModel):
    checksumVerified: Optional[bool] = Field(None, description="Whether checksum was verified")
    durationSec: Optional[int] = Field(None, description="Duration in seconds")
    restoreMode: Optional[str] = Field(None, description="Mode of restore (e.g., full, partial)")
    validationPassed: Optional[bool] = Field(None, description="Whether post-restore validation passed")


class RestoredDataCollection(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    backupRefId: str = Field(..., description="Reference to _id from backup_data_collections")
    restoredBy: Optional[str] = Field(None, description="User/admin/system who triggered restore")
    databaseType: str = Field(..., description="postgres or mongodb")
    targetDatabase: Optional[str] = Field(None, description="Destination environment, e.g., prod_clone, test_env")
    storagePath: Optional[str] = Field(None, description="Location of backup used for restore")
    collectionsRestored: Optional[List[str]] = Field(default_factory=list, description="List of restored entities")
    status: str = Field(..., description="initiated | in_progress | completed | failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Restore start time")
    completedAt: Optional[datetime] = Field(None, description="Completion time")
    details: Optional[RestoreDetails] = None

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "backupRefId": "653a4f...",
                "restoredBy": "admin_user",
                "databaseType": "postgres",
                "targetDatabase": "prod_clone",
                "storagePath": "s3://backups/prod/snapshot_2025_10_08_weekly.tar.gz",
                "collectionsRestored": ["bookings", "rooms"],
                "status": "completed",
                "timestamp": "2025-11-06T00:00:00Z",
                "completedAt": "2025-11-06T00:30:00Z",
                "details": {"checksumVerified": True, "durationSec": 1800, "restoreMode": "full", "validationPassed": True},
            }
        }
