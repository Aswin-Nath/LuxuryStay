from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.audit_service.audit_service import create_audit, list_audits
from app.schemas.pydantic_models.audit_log import AuditLogModel

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/", response_model=dict)
async def post_audit(payload: AuditLogModel):
    created = await create_audit(payload)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create audit record")
    return created


@router.get("/", response_model=List[dict])
async def get_audits(
    entity: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    changed_by_user_id: Optional[int] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime start"),
    end_ts: Optional[str] = Query(None, description="ISO datetime end"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    results = await list_audits(
        entity=entity,
        entity_id=entity_id,
        action=action,
        changed_by_user_id=changed_by_user_id,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )
    return results
