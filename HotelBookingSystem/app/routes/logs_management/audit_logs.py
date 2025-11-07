from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.audit_service.audit_service import list_audits
from app.schemas.pydantic_models.audit_log import AuditLogModel

router = APIRouter(prefix="/audit", tags=["LOGS"])
# POST for creating audit logs is handled by middleware (app/middlewares/logs_middleware.py)
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
    print("Entity__")
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
