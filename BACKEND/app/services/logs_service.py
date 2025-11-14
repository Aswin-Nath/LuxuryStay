from typing import Any, Dict, List, Optional
from datetime import datetime
from app.schemas.pydantic_models.booking_logs import BookingLogModel
from app.crud.logs import insert_booking_log_record, fetch_booking_logs_filtered


async def create_booking_log(doc: BookingLogModel) -> Dict[str, Any]:
	"""
	Create a booking audit log entry.
	
	Records a booking modification event with details about what changed, who changed it,
	and when. Persists audit trail for compliance and troubleshooting. Converts Pydantic
	model to dictionary for database storage.
	
	Args:
		doc (BookingLogModel): Pydantic model containing booking_id, edit_type, edit_id,
		                        old_values, new_values, approved_by, timestamp, etc.
	
	Returns:
		Dict[str, Any]: The created log record with log_id and persistence timestamp.
	"""
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
	"""
	Retrieve booking audit logs with flexible filtering.
	
	Queries booking modification history with support for filtering by booking, edit type,
	approver, and date range. Useful for compliance audits, troubleshooting, and tracking
	changes to bookings. Results are paginated and sorted by timestamp.
	
	Args:
		booking_id (Optional[int]): Filter by specific booking ID.
		edit_id (Optional[int]): Filter by specific edit/modification ID.
		edit_type (Optional[str]): Filter by edit type (e.g., CREATED, UPDATED, CANCELLED).
		approved_by (Optional[int]): Filter by user ID who approved the change.
		start_ts (Optional[str]): Filter logs from this timestamp onwards.
		end_ts (Optional[str]): Filter logs up to this timestamp.
		limit (int): Maximum records to return (default 50).
		skip (int): Records to skip for pagination (default 0).
	
	Returns:
		List[Dict[str, Any]]: List of booking log records with change details.
	"""
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
