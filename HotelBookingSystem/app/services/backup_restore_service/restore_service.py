from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.crud.backup_and_restore_management.restore import (
    insert_restore_record,
    fetch_restore_records,
)
from app.schemas.pydantic_models.restored_data_collections import RestoredDataCollection


# ==========================================================
# 🔹 CREATE RESTORE
# ==========================================================

async def create_restore(doc: RestoredDataCollection) -> Dict[str, Any]:
    """Create a restore record using CRUD functions."""
    payload = doc.model_dump(by_alias=True, exclude_none=True)

    if not payload.get("backupRefId"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="backupRefId is required",
        )

    inserted = await insert_restore_record(payload)
    if not inserted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create restore record",
        )

    return inserted


# ==========================================================
# 🔹 LIST RESTORES
# ==========================================================

async def list_restores(
    backupRefId: Optional[str] = None,
    status: Optional[str] = None,
    databaseType: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """List restore entries with optional filters."""
    results = await fetch_restore_records(
        backupRefId=backupRefId,
        status=status,
        databaseType=databaseType,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No restore records found",
        )

    return results
