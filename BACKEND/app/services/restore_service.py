from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.crud.restore import (
    insert_restore_record,
    fetch_restore_records,
)
from app.schemas.pydantic_models.restored_data_collections import RestoredDataCollection


# ==========================================================
# 🔹 CREATE RESTORE
# ==========================================================

async def create_restore(doc: RestoredDataCollection) -> Dict[str, Any]:
    """
    Create a restore operation record from a backup.
    
    Creates a restore record that tracks the restoration of data from a backup snapshot.
    Validates that a backupRefId is provided to link the restore to the original backup.
    Persists restore metadata for tracking and auditing data recovery operations.
    
    Args:
        doc (RestoredDataCollection): Pydantic model containing restore details including
                                      backupRefId, restored_data, target_environment, etc.
    
    Returns:
        Dict[str, Any]: The created restore record with restore_id and operation timestamps.
    
    Raises:
        HTTPException (400): If backupRefId is missing.
        HTTPException (500): If restore record insertion fails.
    """
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
    """
    List restore records with optional filtering.
    
    Retrieves restore operation records with support for filtering by backup reference,
    restore status, database type, and date range. Results are paginated and useful
    for tracking data recovery operations and restoration history.
    
    Args:
        backupRefId (Optional[str]): Filter by specific backup ID being restored from.
        status (Optional[str]): Filter by restore status (e.g., COMPLETED, IN_PROGRESS, FAILED).
        databaseType (Optional[str]): Filter by database type (e.g., POSTGRES, MONGO).
        start_ts (Optional[str]): Filter restores started on or after this timestamp.
        end_ts (Optional[str]): Filter restores started on or before this timestamp.
        limit (int): Maximum number of records to return (default 50).
        skip (int): Number of records to skip for pagination (default 0).
    
    Returns:
        List[Dict[str, Any]]: List of restore records matching the filter criteria.
    
    Raises:
        HTTPException (404): If no restore records found matching filters.
    """
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
