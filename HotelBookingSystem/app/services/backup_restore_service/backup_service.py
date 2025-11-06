from typing import Any, Dict, List, Optional
from pymongo import ASCENDING, DESCENDING
from datetime import datetime

from app.database.mongo_connnection import get_database
from app.schemas.pydantic_models.backup_data_collections import BackupDataCollection


async def create_backup(doc: BackupDataCollection) -> Dict[str, Any]:
	"""Insert a backup_data_collections document and return the inserted document (with _id)."""
	db = get_database()
	collection = db.backup_data_collections
	# Use dict for broad pydantic compatibility
	try:
		payload = doc.dict(by_alias=True, exclude_none=True)
	except Exception:
		payload = doc.model_dump(by_alias=True, exclude_none=True)
	result = await collection.insert_one(payload)
	inserted = await collection.find_one({"_id": result.inserted_id})
	return inserted


async def list_backups(
	snapshotName: Optional[str] = None,
	triggerType: Optional[str] = None,
	status: Optional[str] = None,
	databaseType: Optional[str] = None,
	start_ts: Optional[str] = None,
	end_ts: Optional[str] = None,
	limit: int = 50,
	skip: int = 0,
) -> List[Dict[str, Any]]:
	"""Query backup_data_collections using simple filter parameters.

	start_ts and end_ts should be ISO datetime strings; caller may pass strings.
	"""
	db = get_database()
	collection = db.backup_data_collections
	filt: Dict[str, Any] = {}
	if snapshotName:
		filt["snapshotName"] = {"$regex": snapshotName, "$options": "i"}
	if triggerType:
		filt["triggerType"] = triggerType
	if status:
		filt["status"] = status
	if databaseType:
		filt["databaseType"] = databaseType
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
			filt["timestamp"] = ts_filter

	cursor = collection.find(filt).sort("timestamp", DESCENDING).skip(int(skip)).limit(int(limit))
	results = []
	async for doc in cursor:
		results.append(doc)
	return results
