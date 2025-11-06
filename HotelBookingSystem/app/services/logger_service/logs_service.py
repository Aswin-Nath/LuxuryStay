from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.mongo_connnection import get_database
from app.schemas.pydantic_models.booking_logs import BookingLogModel


async def create_booking_log(doc: BookingLogModel) -> Dict[str, Any]:
	"""Insert a booking_logs document and return the inserted document."""
	db = get_database()
	collection = db.booking_logs
	payload = doc.dict(by_alias=True, exclude_none=True)
	result = await collection.insert_one(payload)
	inserted = await collection.find_one({"_id": result.inserted_id})
	return inserted


async def list_booking_logs(
	booking_id: Optional[int] = None,
	edit_id: Optional[int] = None,
	edit_type: Optional[str] = None,
	approved_by: Optional[int] = None,
	start_ts: Optional[str] = None,
	end_ts: Optional[str] = None,
	limit: int = 50,
	skip: int = 0,
) -> List[Dict[str, Any]]:
	"""Query booking_logs collection using simple filters."""
	db = get_database()
	collection = db.booking_logs
	filt: Dict[str, Any] = {}
	if booking_id is not None:
		filt["booking_id"] = int(booking_id)
	if edit_id is not None:
		filt["edit_id"] = int(edit_id)
	if edit_type:
		filt["edit_type"] = edit_type
	if approved_by is not None:
		filt["approved_by"] = int(approved_by)

	if start_ts or end_ts:
		ts_filter: Dict[str, Any] = {}
		try:
			if start_ts:
				ts_filter["$gte"] = datetime.fromisoformat(start_ts)
			if end_ts:
				ts_filter["$lte"] = datetime.fromisoformat(end_ts)
		except Exception:
			# fall back to no timestamp filtering if parse fails
			ts_filter = {}

		if ts_filter:
			filt["logged_at"] = ts_filter

	cursor = collection.find(filt).sort("logged_at", -1).skip(int(skip)).limit(int(limit))
	results = []
	async for doc in cursor:
		results.append(doc)
	return results

