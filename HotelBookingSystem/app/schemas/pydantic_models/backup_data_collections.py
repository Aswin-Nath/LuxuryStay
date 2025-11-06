from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class BackupDetails(BaseModel):
    durationSec: Optional[int] = Field(None, description="Duration in seconds")
    compression: Optional[str] = Field(None, description="Compression used, e.g. gzip")
    retentionDays: Optional[int] = Field(None, description="Retention in days")
    verified: Optional[bool] = Field(None, description="Checksum/validation result")


class BackupDataCollection(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    snapshotName: str = Field(..., description="Logical name for the snapshot, e.g. snapshot_2025_10_08_weekly")
    initiatedBy: Optional[str] = Field(None, description="User/admin/system that triggered the backup")
    triggerType: str = Field(..., description="manual | scheduled")
    scheduleType: Optional[str] = Field(None, description="daily | weekly | monthly | custom (nullable; used for scheduled)")
    databaseType: str = Field(..., description="postgres or mongodb")
    collectionsIncluded: Optional[List[str]] = Field(default_factory=list, description="List of collections/tables included in backup")
    storagePath: Optional[str] = Field(None, description="Backup file location (local or cloud)")
    sizeMB: Optional[float] = Field(None, description="Backup file size in MB")
    checksum: Optional[str] = Field(None, description="Checksum (SHA256/MD5) for integrity")
    status: str = Field(..., description="pending | in_progress | completed | failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Backup start time")
    completedAt: Optional[datetime] = Field(None, description="Completion time")
    details: Optional[BackupDetails] = None

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "snapshotName": "snapshot_2025_10_08_weekly",
                "initiatedBy": "system",
                "triggerType": "scheduled",
                "scheduleType": "weekly",
                "databaseType": "mongodb",
                "collectionsIncluded": ["bookings", "rooms"],
                "storagePath": "s3://backups/prod/snapshot_2025_10_08_weekly.tar.gz",
                "sizeMB": 1534.2,
                "checksum": "abc123...",
                "status": "completed",
                "timestamp": "2025-11-06T00:00:00Z",
                "completedAt": "2025-11-06T00:25:00Z",
                "details": {"durationSec": 1500, "compression": "gzip", "retentionDays": 30, "verified": True},
            }
        }
