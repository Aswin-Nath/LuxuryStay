from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.mongo_connnection import get_database
from app.schemas.pydantic_models.audit_log import AuditLogModel


async def create_audit(doc: AuditLogModel) -> Dict[str, Any]:
	"""Insert an audit_log document and return the inserted document."""
	db = get_database()
	collection = db.audit_log
	payload = doc.dict(by_alias=True, exclude_none=True)
	result = await collection.insert_one(payload)
	inserted = await collection.find_one({"_id": result.inserted_id})
	return inserted


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
	"""Query audit_log collection using simple filters.

	start_ts and end_ts are ISO datetime strings.
	"""
	db = get_database()
	collection = db.audit_log
	filt: Dict[str, Any] = {}
	if entity:
		filt["entity"] = entity
	if entity_id:
		filt["entity_id"] = entity_id
	if action:
		filt["action"] = action
	if changed_by_user_id is not None:
		filt["changed_by_user_id"] = int(changed_by_user_id)

	if start_ts or end_ts:
		ts_filter: Dict[str, Any] = {}
		try:
			if start_ts:
				ts_filter["$gte"] = datetime.fromisoformat(start_ts)
			if end_ts:
				ts_filter["$lte"] = datetime.fromisoformat(end_ts)
		except Exception:
			ts_filter = {}

		if ts_filter:
			filt["created_at"] = ts_filter

	cursor = collection.find(filt).sort("created_at", -1).skip(int(skip)).limit(int(limit))
	results = []
	async for doc in cursor:
		results.append(doc)
	return results

