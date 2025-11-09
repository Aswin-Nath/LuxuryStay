from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ==========================================================
# 🔹 CUSTOMER REPORTS (Direct SQL, not via views)
# ==========================================================

async def fetch_customer_booking_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch booking summary for a customer directly from base tables.
    """
    base_sql = """
        SELECT 
            b.booking_id,
            u.user_id,
            u.full_name AS customer_name,
            string_agg(DISTINCT rt.type_name::text, ', ') AS booked_room_types,
            COUNT(brm.room_id) AS total_rooms,
            b.check_in,
            b.check_out,
            b.total_price,
            b.status,
            b.created_at,
            b.updated_at
        FROM bookings b
        LEFT JOIN users u ON b.user_id = u.user_id
        LEFT JOIN booking_room_map brm ON brm.booking_id = b.booking_id
        LEFT JOIN room_types rt ON rt.room_type_id = brm.room_type_id
        WHERE b.is_deleted = FALSE AND b.user_id = :user_id
        GROUP BY b.booking_id, u.user_id, u.full_name
    """

    if entity_id:
        sql = text(base_sql + " HAVING b.booking_id = :entity_id LIMIT 1")
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text(base_sql + " ORDER BY b.created_at DESC LIMIT :limit OFFSET :offset")
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def fetch_customer_payment_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch payment summary for a customer directly from base tables.
    """
    base_sql = """
        SELECT 
            p.payment_id,
            p.booking_id,
            u.user_id,
            u.full_name AS customer_name,
            pmu.name AS payment_method,
            p.amount,
            p.status AS payment_status,
            p.transaction_reference,
            p.payment_date
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        JOIN payment_method_utility pmu ON p.method_id = pmu.method_id
        JOIN bookings b ON b.booking_id = p.booking_id
        WHERE p.is_deleted = FALSE AND b.is_deleted = FALSE AND p.user_id = :user_id
    """

    if entity_id:
        sql = text(base_sql + " AND p.payment_id = :entity_id LIMIT 1")
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text(base_sql + " ORDER BY p.payment_date DESC LIMIT :limit OFFSET :offset")
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def fetch_customer_refund_summary(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch refund summary for a customer directly from base tables.
    """
    base_sql = """
        SELECT 
            r.refund_id,
            r.booking_id,
            u.user_id,
            u.full_name AS customer_name,
            r.type AS refund_type,
            r.status AS refund_status,
            r.refund_amount,
            r.initiated_at,
            r.processed_at,
            r.completed_at,
            pmu.name AS transaction_method,
            r.transaction_number,
            r.remarks
        FROM refunds r
        JOIN users u ON r.user_id = u.user_id
        LEFT JOIN payment_method_utility pmu ON r.transaction_method_id = pmu.method_id
        WHERE r.is_deleted = FALSE AND r.user_id = :user_id
    """

    if entity_id:
        sql = text(base_sql + " AND r.refund_id = :entity_id LIMIT 1")
        params = {"entity_id": entity_id, "user_id": user_id}
    else:
        sql = text(base_sql + " ORDER BY r.initiated_at DESC LIMIT :limit OFFSET :offset")
        params = {"user_id": user_id, "limit": limit, "offset": offset}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


# ==========================================================
# 🔹 ADMIN REPORTS (Direct SQL, not via views)
# ==========================================================

async def fetch_admin_booking_performance(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    room_type: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Admin booking performance: aggregated bookings, revenue, cancellations, completions.
    """
    base_sql = """
        SELECT 
            rt.type_name AS room_type,
            COUNT(DISTINCT b.booking_id) AS total_bookings,
            SUM(b.total_price) AS total_revenue,
            SUM(CASE WHEN b.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_bookings,
            SUM(CASE WHEN b.status = 'CONFIRMED' THEN 1 ELSE 0 END) AS active_bookings,
            SUM(CASE WHEN b.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_bookings,
            DATE(b.created_at) AS booking_date
        FROM bookings b
        JOIN booking_room_map brm ON brm.booking_id = b.booking_id
        JOIN room_types rt ON brm.room_type_id = rt.room_type_id
        WHERE b.is_deleted = FALSE
    """

    where_clauses = []
    params: Dict[str, Any] = {}

    if date_from:
        where_clauses.append("DATE(b.created_at) >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("DATE(b.created_at) <= :date_to")
        params["date_to"] = date_to
    if room_type:
        where_clauses.append("rt.type_name = :room_type")
        params["room_type"] = room_type

    if where_clauses:
        base_sql += " AND " + " AND ".join(where_clauses)

    sql = text(base_sql + """
        GROUP BY rt.type_name, DATE(b.created_at)
        ORDER BY DATE(b.created_at) DESC
        LIMIT :limit
    """)
    params["limit"] = limit

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def fetch_admin_revenue_summary(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Admin revenue summary: total collected, refunded, net revenue per day.
    """
    base_sql = """
        SELECT 
            DATE(p.payment_date) AS payment_date,
            SUM(p.amount) AS total_collected,
            COALESCE(SUM(r.refund_amount), 0) AS total_refunded,
            SUM(p.amount) - COALESCE(SUM(r.refund_amount), 0) AS net_revenue
        FROM payments p
        LEFT JOIN refunds r ON p.booking_id = r.booking_id
        WHERE p.is_deleted = FALSE
    """

    where_clauses = []
    params: Dict[str, Any] = {}

    if date_from:
        where_clauses.append("DATE(p.payment_date) >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("DATE(p.payment_date) <= :date_to")
        params["date_to"] = date_to

    if where_clauses:
        base_sql += " AND " + " AND ".join(where_clauses)

    sql = text(base_sql + """
        GROUP BY DATE(p.payment_date)
        ORDER BY DATE(p.payment_date) DESC
        LIMIT :limit
    """)
    params["limit"] = limit

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def fetch_admin_refund_summary(
    db: AsyncSession,
    limit: int = 500,
    entity_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Admin refund summary: refund details with total processing time.
    """
    base_sql = """
        SELECT 
            r.refund_id,
            r.booking_id,
            u.full_name AS customer_name,
            r.refund_amount,
            r.type AS refund_type,
            r.status AS refund_status,
            r.completed_at - r.initiated_at AS total_processing_time,
            r.initiated_at,
            r.completed_at
        FROM refunds r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.is_deleted = FALSE
    """

    if entity_id:
        sql = text(base_sql + " AND r.refund_id = :entity_id LIMIT 1")
        params = {"entity_id": entity_id}
    else:
        sql = text(base_sql + " ORDER BY r.initiated_at DESC LIMIT :limit")
        params = {"limit": limit}

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


async def fetch_admin_payment_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Admin payment summary: success/failure rate by payment method.
    """
    sql = text("""
        SELECT 
            pmu.name AS payment_method,
            COUNT(p.payment_id) AS total_transactions,
            SUM(CASE WHEN p.status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
            SUM(CASE WHEN p.status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
            ROUND(SUM(CASE WHEN p.status = 'SUCCESS' THEN 1 ELSE 0 END)::NUMERIC / 
                  COUNT(p.payment_id)::NUMERIC * 100, 2) AS success_rate
        FROM payments p
        JOIN payment_method_utility pmu ON p.method_id = pmu.method_id
        WHERE p.is_deleted = FALSE
        GROUP BY pmu.name
        ORDER BY success_rate DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(row) for row in result.mappings().all()]


async def fetch_admin_review_summary(
    db: AsyncSession,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Admin review summary: aggregated review metrics by room type.
    """
    sql = text("""
        SELECT 
            rt.type_name AS room_type,
            COUNT(rv.review_id) AS total_reviews,
            ROUND(AVG(rv.rating), 2) AS average_rating,
            SUM(CASE WHEN rv.rating >= 4 THEN 1 ELSE 0 END) AS positive_reviews,
            SUM(CASE WHEN rv.rating <= 2 THEN 1 ELSE 0 END) AS negative_reviews
        FROM reviews rv
        JOIN room_types rt ON rv.room_type_id = rt.room_type_id
        GROUP BY rt.type_name
        ORDER BY average_rating DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"limit": limit})
    return [dict(row) for row in result.mappings().all()]
