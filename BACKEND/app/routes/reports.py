from fastapi import APIRouter, Depends, Query, Security
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from io import BytesIO

# ---------------------------------------------------------------------------
# 🔗 Imports
# ---------------------------------------------------------------------------
from app.database.postgres_connection import get_db
from app.dependencies.authentication import (
	get_current_user,
	check_permission,
)
from app.models.sqlalchemy_schemas.users import Users
from app.services.report_management_service import (
	get_admin_booking_performance,
	get_admin_revenue_summary,
	get_admin_refund_summary,
	get_admin_payment_summary,
	get_admin_review_summary,
	get_customer_booking_summary,
	get_customer_payment_summary,
	get_customer_refund_summary,
	format_report_response,
)

router = APIRouter(prefix="/reports", tags=["REPORTS"])

# ============================================================================
# 🔹 ADMIN REPORTS (Protected by permission scopes)
# ============================================================================

@router.get("/admin/booking_performance")
async def booking_performance(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	room_type: Optional[str] = Query(None),
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
	_permissions: dict = Security(check_permission, scopes=["ANALYTICS_VIEW:READ"]),
):
	"""
	Generate admin booking performance report.
	
	Creates detailed report on booking metrics including occupancy rates, total bookings,
	average stay duration, and revenue. Can be exported as PDF or returned as JSON.
	
	Args:
		date_from (Optional[str]): Start date for report (YYYY-MM-DD format).
		date_to (Optional[str]): End date for report (YYYY-MM-DD format).
		room_type (Optional[str]): Filter report by specific room type.
		pdf (bool): If True, export as PDF file (default: False).
		limit (int): Maximum records to include (default: 200, max: 2000).
		db (AsyncSession): Database session dependency.
		_permissions (dict): Security token with ANALYTICS_VIEW:READ permission.
	
	Returns:
		dict or StreamingResponse: Report data as JSON or PDF file.
	
	Raises:
		HTTPException (403): If user lacks ANALYTICS_VIEW:READ permission.
		HTTPException (400): If invalid date format.
	"""
	items = await get_admin_booking_performance(db, date_from=date_from, date_to=date_to, room_type=room_type, limit=limit)
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Booking Performance")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=booking_performance_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/admin/revenue_summary")
async def revenue_summary(
	date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
	date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
	_permissions: dict = Security(check_permission, scopes=["ANALYTICS_VIEW:READ"]),
):
	"""
	Generate admin revenue summary report.
	
	Provides revenue analytics including total revenue, payment breakdown by method,
	and revenue trends over time. Supports PDF export.
	
	Args:
		date_from (Optional[str]): Start date (YYYY-MM-DD format).
		date_to (Optional[str]): End date (YYYY-MM-DD format).
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Maximum records (default: 200, max: 2000).
		db (AsyncSession): Database session dependency.
		_permissions (dict): Security token with ANALYTICS_VIEW:READ permission.
	
	Returns:
		dict or StreamingResponse: Revenue report as JSON or PDF.
	
	Raises:
		HTTPException (403): If user lacks permissions.
	"""
	items = await get_admin_revenue_summary(db, date_from=date_from, date_to=date_to, limit=limit)
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Revenue Summary")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=revenue_summary_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/admin/refunds_summary")
async def refunds_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	entity_id: Optional[int] = Query(None, description="Optional refund_id or booking_id to fetch a single refund record"),
	db: AsyncSession = Depends(get_db),
	_permissions: dict = Security(check_permission, scopes=["ANALYTICS_VIEW:READ"]),
):
	"""
	Generate admin refund summary report.
	
	Generates refund analytics including total refunds, refund reasons distribution,
	and refund rate trends. Can fetch individual refund or summary report.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Maximum records (default: 200, max: 2000).
		entity_id (Optional[int]): Specific refund_id or booking_id to fetch single record.
		db (AsyncSession): Database session dependency.
		_permissions (dict): Security token with ANALYTICS_VIEW:READ permission.
	
	Returns:
		dict or StreamingResponse: Refund report as JSON or PDF.
	
	Raises:
		HTTPException (403): If user lacks permissions.
		HTTPException (404): If entity_id specified but not found.
	"""
	items = await get_admin_refund_summary(db, limit=limit, entity_id=entity_id)
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Refund Summary")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=refund_summary_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/admin/payment_summary")
async def payment_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
	_permissions: dict = Security(check_permission, scopes=["ANALYTICS_VIEW:READ"]),
):
	"""
	Generate admin payment summary report.
	
	Generates payment transaction analysis including success/failure rates,
	payment method breakdown, and transaction trends.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Maximum records (default: 200, max: 2000).
		db (AsyncSession): Database session dependency.
		_permissions (dict): Security token with ANALYTICS_VIEW:READ permission.
	
	Returns:
		dict or StreamingResponse: Payment report as JSON or PDF.
	
	Raises:
		HTTPException (403): If user lacks permissions.
	"""
	items = await get_admin_payment_summary(db, limit=limit)
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Payment Summary")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=payment_summary_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/admin/review_summary")
async def review_summary(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(200, ge=1, le=2000),
	db: AsyncSession = Depends(get_db),
	_permissions: dict = Security(check_permission, scopes=["ANALYTICS_VIEW:READ"]),
):
	"""
	Generate admin review summary report.
	
	Generates review metrics including average rating, total reviews,
	rating distribution by stars, and trending feedback.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Maximum records (default: 200, max: 2000).
		db (AsyncSession): Database session dependency.
		_permissions (dict): Security token with ANALYTICS_VIEW:READ permission.
	
	Returns:
		dict or StreamingResponse: Review report as JSON or PDF.
	
	Raises:
		HTTPException (403): If user lacks permissions.
	"""
	items = await get_admin_review_summary(db, limit=limit)
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="Review Summary")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=review_summary_report.pdf"})
	return await format_report_response(items, export_pdf=False)

# ============================================================================
# 🔹 CUSTOMER REPORTS (Authenticated user)
# ============================================================================

@router.get("/customer/bookings")
async def customer_bookings(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional booking_id to fetch a single booking"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
	_permissions: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
	"""
	Generate customer personal booking summary.
	
	Provides authenticated user's booking statistics including total bookings,
	total spent, average rating given, and upcoming bookings.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Records per page (default: 50, max: 1000).
		offset (int): Pagination offset (default: 0).
		entity_id (Optional[int]): Specific booking_id to fetch single booking.
		db (AsyncSession): Database session dependency.
		current_user (Users): Authenticated user (report owner).
	
	Returns:
		dict or StreamingResponse: Booking summary as JSON or PDF.
	
	Raises:
		HTTPException (404): If entity_id specified but not found or not owned by user.
	"""
	items = await get_customer_booking_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Bookings")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=customer_bookings_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/customer/payments")
async def customer_payments(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional payment_id to fetch a single payment"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
	_permissions: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),

):
	"""
	Generate customer personal payment summary.
	
	Provides authenticated user's payment history analytics including total paid,
	average transaction amount, and payment method breakdown.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Records per page (default: 50, max: 1000).
		offset (int): Pagination offset (default: 0).
		entity_id (Optional[int]): Specific payment_id to fetch single payment.
		db (AsyncSession): Database session dependency.
		current_user (Users): Authenticated user (report owner).
	
	Returns:
		dict or StreamingResponse: Payment summary as JSON or PDF.
	
	Raises:
		HTTPException (404): If entity_id specified but not found or not owned by user.
	"""
	items = await get_customer_payment_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Payments")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=customer_payments_report.pdf"})
	return await format_report_response(items, export_pdf=False)


@router.get("/customer/refunds")
async def customer_refunds(
	pdf: bool = Query(False, description="Export as PDF if true"),
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional refund_id to fetch a single refund"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
	_permissions: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
	"""
	Generate customer personal refund summary.
	
	Provides authenticated user's refund history including total refunds received,
	refund reasons, and refund processing timeline.
	
	Args:
		pdf (bool): Export as PDF if True (default: False).
		limit (int): Records per page (default: 50, max: 1000).
		offset (int): Pagination offset (default: 0).
		entity_id (Optional[int]): Specific refund_id to fetch single refund.
		db (AsyncSession): Database session dependency.
		current_user (Users): Authenticated user (report owner).
	
	Returns:
		dict or StreamingResponse: Refund summary as JSON or PDF.
	
	Raises:
		HTTPException (404): If entity_id specified but not found or not owned by user.
	"""
	items = await get_customer_refund_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	if entity_id is not None and not pdf:
		return items[0] if items else {}
	if pdf:
		pdf_data = await format_report_response(items, export_pdf=True, report_title="My Refunds")
		return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=customer_refunds_report.pdf"})
	return await format_report_response(items, export_pdf=False)
