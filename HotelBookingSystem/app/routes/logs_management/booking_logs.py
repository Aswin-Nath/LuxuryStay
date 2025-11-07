from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.logger_service.logs_service import list_booking_logs
from app.schemas.pydantic_models.booking_logs import BookingLogModel

router = APIRouter(prefix="/booking_logs", tags=["LOGS"])

# POST for creating booking logs is handled by middleware (app/middlewares/logs_middleware.py)
@router.get("/", response_model=List[dict])
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
