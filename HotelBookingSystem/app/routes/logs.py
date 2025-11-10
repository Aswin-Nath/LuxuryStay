from fastapi import APIRouter, Query
from typing import List, Optional

from app.services.logs_service import list_booking_logs
from app.services.audit_service import list_audits
from app.schemas.pydantic_models.booking_logs import BookingLogModel
from app.schemas.pydantic_models.audit_log import AuditLogModel

router = APIRouter(prefix="/logs", tags=["LOGS"])

# =====================================================================
# 🔹 BOOKING LOGS
# =====================================================================
@router.get("/booking", response_model=List[dict])
async def get_booking_logs(
    booking_id: Optional[int] = Query(None),
    edit_id: Optional[int] = Query(None),
    edit_type: Optional[str] = Query(None),
    approved_by: Optional[int] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime start"),
    end_ts: Optional[str] = Query(None, description="ISO datetime end"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    results = await list_booking_logs(
        booking_id=booking_id,
        edit_id=edit_id,
        edit_type=edit_type,
        approved_by=approved_by,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )
    return results


# =====================================================================
# 🔹 AUDIT LOGS
# =====================================================================
@router.get("/audit", response_model=List[dict])
async def get_audit_logs(
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
