from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.services.report_management.report_management_service import (
	get_customer_booking_summary,
	get_customer_payment_summary,
	get_customer_refund_summary,
)

router = APIRouter(prefix="/reports/customer", tags=["REPORTS_CUSTOMER"])

@router.get("/bookings")
async def customer_bookings(
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional booking_id to fetch a single booking"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return booking summary rows for the authenticated customer. If entity_id is provided, return that booking only."""
	items = await get_customer_booking_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	# If entity_id requested return single object or 404-like empty
	if entity_id is not None:
		return items[0] if items else {}
	return {"count": len(items), "items": items}

@router.get("/payments")
async def customer_payments(
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional payment_id to fetch a single payment"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return payment summary rows for the authenticated customer. If entity_id is provided, return that payment only."""
	items = await get_customer_payment_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	if entity_id is not None:
		return items[0] if items else {}
	return {"count": len(items), "items": items}

@router.get("/refunds")
async def customer_refunds(
	limit: int = Query(50, ge=1, le=1000),
	offset: int = Query(0, ge=0),
	entity_id: Optional[int] = Query(None, description="Optional refund_id to fetch a single refund"),
	db: AsyncSession = Depends(get_db),
	current_user: Users = Depends(get_current_user),
):
	"""Return refund summary rows for the authenticated customer. If entity_id is provided, return that refund only."""
	items = await get_customer_refund_summary(db, current_user.user_id, limit=limit, offset=offset, entity_id=entity_id)
	if entity_id is not None:
		return items[0] if items else {}
	return {"count": len(items), "items": items}

