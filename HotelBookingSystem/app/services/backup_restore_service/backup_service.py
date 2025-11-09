from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

# CRUD imports
from app.crud.backup_and_restore_management.backup import insert_backup_record, fetch_backup_records

# Schema import
from app.schemas.pydantic_models.backup_data_collections import BackupDataCollection


# ==========================================================
# 🔹 CREATE BACKUP
# ==========================================================

async def create_backup(doc: BackupDataCollection) -> Dict[str, Any]:
    """Create a new backup record using CRUD."""
    try:
        backup_payload = doc.model_dump(by_alias=True, exclude_none=True)
    except Exception:
        backup_payload = doc.dict(by_alias=True, exclude_none=True)

    # Basic validation
    if not backup_payload.get("snapshotName"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="snapshotName is required",
        )
    if not backup_payload.get("databaseType"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="databaseType is required",
        )

    created_backup_record = await insert_backup_record(backup_payload)
    if not created_backup_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to insert backup record",
        )

    return created_backup_record


# ==========================================================
# 🔹 LIST BACKUPS
# ==========================================================

async def list_backups(
    snapshotName: Optional[str] = None,
    triggerType: Optional[str] = None,
    status: Optional[str] = None,
    databaseType: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """List all backups with optional filters."""
    backup_records = await fetch_backup_records(
        snapshotName=snapshotName,
        triggerType=triggerType,
        status=status,
        databaseType=databaseType,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )

    if not backup_records:
        raise HTTPException(
            status_code=404,
            detail="No backup records found",
        )

    return backup_records
