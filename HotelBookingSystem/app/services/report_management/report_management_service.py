from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

# CRUD imports
from app.crud.report_management.reports import (
    fetch_customer_booking_summary,
    fetch_customer_payment_summary,
    fetch_customer_refund_summary,
    fetch_admin_booking_performance,
    fetch_admin_revenue_summary,
    fetch_admin_refund_summary,
    fetch_admin_payment_summary,
    fetch_admin_review_summary,
)

# ==========================================================
# 🔹 CUSTOMER REPORT SERVICES
# ==========================================================

async def get_customer_booking_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch bookings for a customer via vw_customer_booking_summary.
    """
    return await fetch_customer_booking_summary(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        entity_id=entity_id,
    )


async def get_customer_payment_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch payments for a customer via vw_customer_payment_summary.
    """
    return await fetch_customer_payment_summary(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        entity_id=entity_id,
    )


async def get_customer_refund_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch refunds for a customer via vw_customer_refund_summary.
    """
    return await fetch_customer_refund_summary(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        entity_id=entity_id,
    )


# ==========================================================
# 🔹 ADMIN REPORT SERVICES
# ==========================================================

async def get_admin_booking_performance(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    room_type: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch admin booking performance metrics via vw_admin_booking_performance.
    """
    return await fetch_admin_booking_performance(
        db=db,
        date_from=date_from,
        date_to=date_to,
        room_type=room_type,
        limit=limit,
    )


async def get_admin_revenue_summary(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch admin revenue summary via vw_admin_revenue_summary.
    """
    return await fetch_admin_revenue_summary(
        db=db,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


async def get_admin_refund_summary(
    db: AsyncSession,
    limit: int = 500,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch admin refund SLA tracking data via vw_admin_refund_summary.
    """
    return await fetch_admin_refund_summary(
        db=db,
        limit=limit,
        entity_id=entity_id,
    )


async def get_admin_payment_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch admin payment distribution data via vw_admin_payment_summary.
    """
    return await fetch_admin_payment_summary(
        db=db,
        limit=limit,
    )


async def get_admin_review_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Service: Fetch admin review analytics via vw_admin_review_summary.
    """
    return await fetch_admin_review_summary(
        db=db,
        limit=limit,
    )
