from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import ensure_not_basic_user
from app.services.report_management.report_management_service import (
	get_admin_booking_performance,
	get_admin_revenue_summary,
	get_admin_refund_summary,
	get_admin_payment_summary,
	get_admin_review_summary,
)

router = APIRouter(prefix="/reports/admin", tags=["REPORTS_ADMIN"], dependencies=[Depends(ensure_not_basic_user)])

@router.get("/booking_performance")
async def booking_performance(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	room_type: Optional[str] = Query(None),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_booking_performance(db, date_from=date_from, date_to=date_to, room_type=room_type, limit=limit)
	return {"count": len(items), "items": items}

@router.get("/revenue_summary")
async def revenue_summary(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_revenue_summary(db, date_from=date_from, date_to=date_to, limit=limit)
	return {"count": len(items), "items": items}

@router.get("/refunds_summary")
async def refunds_summary(
	limit: int = Query(200, ge=1, le=2000),
	entity_id: Optional[int] = Query(None, description="Optional refund_id or booking_id to fetch a single refund record"),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_refund_summary(db, limit=limit, entity_id=entity_id)
	if entity_id is not None:
		return items[0] if items else {}
	return {"count": len(items), "items": items}

@router.get("/payment_summary")
async def payment_summary(limit: int = Query(200, ge=1, le=2000), db: AsyncSession = Depends(get_db)):
	items = await get_admin_payment_summary(db, limit=limit)
	return {"count": len(items), "items": items}

@router.get("/review_summary")
async def review_summary(limit: int = Query(200, ge=1, le=2000), db: AsyncSession = Depends(get_db)):
	items = await get_admin_review_summary(db, limit=limit)
	return {"count": len(items), "items": items}

