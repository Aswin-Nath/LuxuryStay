from typing import Any, Dict, List, Optional
from app.schemas.pydantic_models.audit_log import AuditLogModel
from app.crud.audit_log.audit import insert_audit_log_record, fetch_audit_logs_filtered


# ==========================================================
# 🔹 CREATE AUDIT LOG
# ==========================================================
async def create_audit(doc: AuditLogModel) -> Dict[str, Any]:
	"""Create a new audit log entry."""
	try:
		payload = doc.model_dump(by_alias=True, exclude_none=True)
	except Exception:
		payload = doc.dict(by_alias=True, exclude_none=True)

	inserted = await insert_audit_log_record(payload)
	return inserted


# ==========================================================
# 🔹 LIST AUDIT LOGS
# ==========================================================
async def list_audits(
	entity: Optional[str] = None,
	entity_id: Optional[str] = None,
	action: Optional[str] = None,
	changed_by_user_id: Optional[int] = None,
	start_ts: Optional[str] = None,
	end_ts: Optional[str] = None,
	limit: int = 50,
	skip: int = 0,
) -> List[Dict[str, Any]]:
	"""List all audit logs with optional filters."""
	return await fetch_audit_logs_filtered(
		entity=entity,
		entity_id=entity_id,
		action=action,
		changed_by_user_id=changed_by_user_id,
		start_ts=start_ts,
		end_ts=end_ts,
		limit=limit,
		skip=skip,
	)
