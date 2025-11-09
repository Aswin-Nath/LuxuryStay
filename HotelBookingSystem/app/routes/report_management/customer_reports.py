from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.services.report_management.report_management_service import (
	get_customer_booking_summary,
	get_customer_payment_summary,
	get_customer_refund_summary,
	format_report_response,
)

router = APIRouter(prefix="/reports/customer", tags=["REPORTS_CUSTOMER"])

# ============================================================================
# 🔹 READ - Customer booking summary report
# ============================================================================
@router.get("/bookings")
async def customer_bookings(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional booking_id to fetch a single booking"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return booking summary rows for the authenticated customer. If entity_id is provided, return that booking only."""
	items = await get_customer_booking_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Bookings")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=customer_bookings_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Customer payment summary report
# ============================================================================
@router.get("/payments")
async def customer_payments(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional payment_id to fetch a single payment"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return payment summary rows for the authenticated customer. If entity_id is provided, return that payment only."""
	items = await get_customer_payment_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Payments")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=customer_payments_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 READ - Customer refund summary report
# ============================================================================
@router.get("/refunds")
async def customer_refunds(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional refund_id to fetch a single refund"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return refund summary rows for the authenticated customer. If entity_id is provided, return that refund only."""
	items = await get_customer_refund_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Refunds")
		return StreamingResponse(
			BytesIO(pdf_data),
			media_type="application/pdf",
			headers={"Content-Disposition": "attachment; filename=customer_refunds_report.pdf"}
		)
	
	return await format_report_response(items, export_pdf=False)

