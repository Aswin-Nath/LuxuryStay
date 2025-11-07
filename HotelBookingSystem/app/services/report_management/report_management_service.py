from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ==========================================================
# 🔹 CUSTOMER REPORTS
# ==========================================================

async def get_customer_booking_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch bookings for the authenticated customer from view vw_customer_booking_summary.

    If entity_id is provided, return the single matching booking_id for that user.
    """
    if entity_id is not None:
        sql = text("""
            SELECT *
            FROM vw_customer_booking_summary
            WHERE booking_id = :entity_id AND user_id = :user_id
            LIMIT 1
        """)
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text("""
            SELECT *
            FROM vw_customer_booking_summary
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def get_customer_payment_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch payments for the authenticated customer from view vw_customer_payment_summary.

    If entity_id is provided, treat it as payment_id and return that single row for the user.
    """
    if entity_id is not None:
        sql = text("""
            SELECT *
            FROM vw_customer_payment_summary
            WHERE payment_id = :entity_id AND user_id = :user_id
            LIMIT 1
        """)
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text("""
            SELECT *
            FROM vw_customer_payment_summary
            WHERE user_id = :user_id
            ORDER BY payment_date DESC
            LIMIT :limit OFFSET :offset
        """)
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def get_customer_refund_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch refunds for the authenticated customer from view vw_customer_refund_summary.

    If entity_id is provided, treat it as refund_id and return that single row for the user.
    """
    if entity_id is not None:
        sql = text("""
            SELECT *
            FROM vw_customer_refund_summary
            WHERE refund_id = :entity_id AND user_id = :user_id
            LIMIT 1
        """)
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text("""
            SELECT *
            FROM vw_customer_refund_summary
            WHERE user_id = :user_id
            ORDER BY initiated_at DESC
            LIMIT :limit OFFSET :offset
        """)
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


# ==========================================================
# 🔹 ADMIN REPORTS
# ==========================================================

async def get_admin_booking_performance(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    room_type: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch admin booking performance metrics from view vw_admin_booking_performance.
    Supports optional date range and room_type filters.
    """
    where_clauses = []
    params: Dict[str, Any] = {}

    if date_from:
        where_clauses.append("booking_date >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("booking_date <= :date_to")
        params["date_to"] = date_to

    if room_type:
        where_clauses.append("room_type = :room_type")
        params["room_type"] = room_type

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = text(f"""
        SELECT *
        FROM vw_admin_booking_performance
        {where_sql}
        ORDER BY booking_date DESC
        LIMIT :limit
    """)
    params["limit"] = limit

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def get_admin_revenue_summary(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch admin revenue analytics from view vw_admin_revenue_summary.
    Supports optional date range filters.
    """
    where_clauses = []
    params: Dict[str, Any] = {}

    if date_from:
        where_clauses.append("payment_date >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("payment_date <= :date_to")
        params["date_to"] = date_to

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = text(f"""
        SELECT *
        FROM vw_admin_revenue_summary
        {where_sql}
        ORDER BY payment_date DESC
        LIMIT :limit
    """)
    params["limit"] = limit

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def get_admin_refund_summary(
    db: AsyncSession,
    limit: int = 500,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch refund SLA tracking data for admins from vw_admin_refund_summary.

    If entity_id is provided, attempt to return the refund by refund_id.
    """
    if entity_id is not None:
        sql = text("""
            SELECT *
            FROM vw_admin_refund_summary
            WHERE (refund_id = :entity_id)
            LIMIT 1
        """)
        params = {"entity_id": entity_id}
    else:
        sql = text("""
            SELECT *
            FROM vw_admin_refund_summary
            ORDER BY initiated_at DESC
            LIMIT :limit
        """)
        params = {"limit": limit}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def get_admin_payment_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch payment success/failure distribution from vw_admin_payment_summary.
    """
    sql = text("""
        SELECT *
        FROM vw_admin_payment_summary
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(row) for row in result.mappings().all()]


async def get_admin_review_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch review analytics for room types from vw_admin_review_summary.
    """
    sql = text("""
        SELECT *
        FROM vw_admin_review_summary
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(row) for row in result.mappings().all()]
