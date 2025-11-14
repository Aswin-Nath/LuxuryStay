from fastapi import APIRouter, Query,Security
from app.dependencies.authentication import check_permission
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

    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"])

):
    """
    Retrieve booking activity logs with optional filters.
    
    Fetches booking-related logs and change history from the system. Supports filtering by
    booking ID, edit ID, edit type, approver, and date range. Useful for audit trails and
    understanding booking change history.
    
    Args:
        booking_id (Optional[int]): Filter logs for specific booking.
        edit_id (Optional[int]): Filter logs for specific edit request.
        edit_type (Optional[str]): Filter by type of edit (ROOM_CHANGE, DATE_CHANGE, etc).
        approved_by (Optional[int]): Filter logs approved by specific user.
        start_ts (Optional[str]): ISO datetime string for start of range.
        end_ts (Optional[str]): ISO datetime string for end of range.
        limit (int): Number of records to return (default: 50, max: 1000).
        skip (int): Number of records to skip for pagination (default: 0).
    
    Returns:
        List[dict]: Array of booking logs with timestamps, changes, and user info.
    
    Raises:
        HTTPException (400): If invalid datetime format provided.
    """
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
    token_payload: dict = Security(check_permission, scopes=["CONTENT_MANAGEMENT:WRITE"])

):
    """
    Retrieve system-wide audit logs with optional filters.
    
    Fetches complete audit trail for all system entities. Logs track all modifications including
    INSERT, UPDATE, DELETE actions with before/after values. Essential for compliance and
    security auditing.
    
    Args:
        entity (Optional[str]): Filter by entity type (booking, review, payment, user, etc).
        entity_id (Optional[str]): Filter by specific entity ID.
        action (Optional[str]): Filter by action type (INSERT, UPDATE, DELETE).
        changed_by_user_id (Optional[int]): Filter by user who made the change.
        start_ts (Optional[str]): ISO datetime string for start of range.
        end_ts (Optional[str]): ISO datetime string for end of range.
        limit (int): Number of records to return (default: 50, max: 1000).
        skip (int): Number of records to skip for pagination (default: 0).
    
    Returns:
        List[dict]: Array of audit log entries with entity info, changes, and timestamps.
    
    Raises:
        HTTPException (400): If invalid datetime format or parameters.
    """
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
