from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from app.database.postgres_connection import get_db
from app.dependencies.authentication import ensure_not_basic_user
from app.services.report_management.report_management_service import (
	get_admin_booking_performance,
	get_admin_revenue_summary,
	get_admin_refund_summary,
	get_admin_payment_summary,
	get_admin_review_summary,
	format_report_response,
)

router = APIRouter(prefix="/reports/admin", tags=["REPORTS_ADMIN"], dependencies=[Depends(ensure_not_basic_user)])

# ============================================================================
# 🔹 READ - Admin booking performance report
# ============================================================================
@router.get("/booking_performance")
async def booking_performance(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	room_type: Optional[str] = Query(None),
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_booking_performance(db, date_from=date_from, date_to=date_to, room_type=room_type, limit=limit)
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Booking Performance")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=booking_performance_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Admin revenue summary report
# ============================================================================
@router.get("/revenue_summary")
async def revenue_summary(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_revenue_summary(db, date_from=date_from, date_to=date_to, limit=limit)
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Revenue Summary")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=revenue_summary_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Admin refund summary report
# ============================================================================
@router.get("/refunds_summary")
async def refunds_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	entity_id: Optional[int] = Query(None, description="Optional refund_id or booking_id to fetch a single refund record"),
	db: AsyncSession = Depends(get_db),
):
	items = await get_admin_refund_summary(db, limit=limit, entity_id=entity_id)
	
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Refund Summary")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=refund_summary_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Admin payment summary report
# ============================================================================
@router.get("/payment_summary")
async def payment_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db)
):
	items = await get_admin_payment_summary(db, limit=limit)
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Payment Summary")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=payment_summary_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Admin review summary report
# ============================================================================
@router.get("/review_summary")
async def review_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db)
):
	items = await get_admin_review_summary(db, limit=limit)
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Review Summary")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=review_summary_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

