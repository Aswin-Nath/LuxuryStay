from typing import Any, Dict, List, Optional
from datetime import datetime
from app.schemas.pydantic_models.booking_logs import BookingLogModel
from app.crud.logs_management.logs import insert_booking_log_record, fetch_booking_logs_filtered


async def create_booking_log(doc: BookingLogModel) -> Dict[str, Any]:
	"""Create a booking log entry (insert + return inserted doc)."""
	try:
		payload = doc.model_dump(by_alias=True, exclude_none=True)
	except Exception:
		payload = doc.dict(by_alias=True, exclude_none=True)

	return await insert_booking_log_record(payload)


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
	"""List booking logs with flexible filters."""
	return await fetch_booking_logs_filtered(
		booking_id=booking_id,
		edit_id=edit_id,
		edit_type=edit_type,
		approved_by=approved_by,
		start_ts=start_ts,
		end_ts=end_ts,
		limit=limit,
		skip=skip,
	)
