from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId

from app.database.mongo_connnection import get_database


# ==========================================================
# 🔹 CREATE
# ==========================================================
async def insert_audit_log_record(payload: Dict[str, Any]) -> Dict[str, Any]:
	"""Insert an audit_log document and return the inserted document."""
	db = get_database()
	collection = db.audit_log
	result = await collection.insert_one(payload)
	inserted = await collection.find_one({"_id": result.inserted_id})
	if inserted and "_id" in inserted and isinstance(inserted["_id"], ObjectId):
		inserted["_id"] = str(inserted["_id"])
	return inserted


# ==========================================================
# 🔹 READ
# ==========================================================
async def fetch_audit_logs_filtered(
	entity: Optional[str] = None,
	entity_id: Optional[str] = None,
	action: Optional[str] = None,
	changed_by_user_id: Optional[int] = None,
	start_ts: Optional[str] = None,
	end_ts: Optional[str] = None,
	limit: int = 50,
	skip: int = 0,
) -> List[Dict[str, Any]]:
	"""Fetch audit logs with filters from MongoDB."""
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
	results: List[Dict[str, Any]] = []
	async for doc in cursor:
		if "_id" in doc and isinstance(doc["_id"], ObjectId):
			doc["_id"] = str(doc["_id"])
		results.append(doc)

	return results
