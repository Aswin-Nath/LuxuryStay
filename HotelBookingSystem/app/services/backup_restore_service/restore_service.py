from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.mongo_connnection import get_database
from app.schemas.pydantic_models.restored_data_collections import RestoredDataCollection


async def create_restore(doc: RestoredDataCollection) -> Dict[str, Any]:
	db = get_database()
	collection = db.restored_data_collections
	payload = doc.dict(by_alias=True, exclude_none=True)
	result = await collection.insert_one(payload)
	inserted = await collection.find_one({"_id": result.inserted_id})
	return inserted


async def list_restores(
	backupRefId: Optional[str] = None,
	status: Optional[str] = None,
	databaseType: Optional[str] = None,
	start_ts: Optional[str] = None,
	end_ts: Optional[str] = None,
	limit: int = 50,
	skip: int = 0,
) -> List[Dict[str, Any]]:
	db = get_database()
	collection = db.restored_data_collections
	filt: Dict[str, Any] = {}
	if backupRefId:
		filt["backupRefId"] = backupRefId
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

	cursor = collection.find(filt).sort("timestamp", -1).skip(int(skip)).limit(int(limit))
	results = []
	async for doc in cursor:
		results.append(doc)
	return results

