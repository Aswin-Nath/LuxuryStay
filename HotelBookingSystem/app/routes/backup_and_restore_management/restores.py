from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional

from app.services.backup_restore_service.restore_service import create_restore, list_restores
from app.schemas.pydantic_models.restored_data_collections import RestoredDataCollection
from app.dependencies.authentication import ensure_not_basic_user
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/restores", tags=["RESTORES"])


@router.post("/", response_model=dict)
async def post_restore(payload: RestoredDataCollection, _ok: bool = Depends(ensure_not_basic_user)):
    created = await create_restore(payload)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create restore record")
    # audit restore create
    try:
        entity_id = f"restore:{created.get('id') or created.get('_id') or ''}"
        await log_audit(entity="restore", entity_id=entity_id, action="INSERT", new_value=created)
    except Exception:
        pass
    return created


@router.get("/", response_model=List[dict])
async def get_restores(
    backupRefId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    databaseType: Optional[str] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime start"),
    end_ts: Optional[str] = Query(None, description="ISO datetime end"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    _ok: bool = Depends(ensure_not_basic_user),
):
    results = await list_restores(
        backupRefId=backupRefId,
        status=status,
        databaseType=databaseType,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )
    return results
