from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.services.backup_restore_service.backup_service import create_backup, list_backups
from app.schemas.pydantic_models.backup_data_collections import BackupDataCollection
from app.dependencies.authentication import ensure_not_basic_user

router = APIRouter(prefix="/backups", tags=["backup"])


@router.post("/", response_model=dict)
async def post_backup(payload: BackupDataCollection, _ok: bool = Depends(ensure_not_basic_user)):
    """Create a backup_data_collections document."""
    created = await create_backup(payload)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create backup record")
    return created


@router.get("/", response_model=List[dict])
async def get_backups(
    snapshotName: Optional[str] = Query(None),
    triggerType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    databaseType: Optional[str] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime string (start)"),
    end_ts: Optional[str] = Query(None, description="ISO datetime string (end)"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    _ok: bool = Depends(ensure_not_basic_user),
):
    """List backups with optional filters and pagination."""
    results = await list_backups(
        snapshotName=snapshotName,
        triggerType=triggerType,
        status=status,
        databaseType=databaseType,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )
    return results
