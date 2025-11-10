from typing import List, Optional, Dict, Any, Union
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

# PDF service import
from app.services.report_management.pdf_service import generate_report_pdf

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
    Retrieve customer booking summary report.
    
    Queries vw_customer_booking_summary view to get paginated booking history for a customer.
    Returns booking details including dates, room types, prices, and status. Optionally filters
    by specific booking entity_id.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The customer's user ID.
        limit (int): Maximum records to return (default 100).
        offset (int): Records to skip for pagination (default 0).
        entity_id (Optional[int]): Filter by specific booking ID (default None = all).
    
    Returns:
        List[Dict[str, Any]]: List of booking records with summary details.
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
    Retrieve customer payment summary report.
    
    Queries vw_customer_payment_summary view to get paginated payment history for a customer.
    Returns payment details including amounts, methods, booking references, and timestamps.
    Optionally filters by specific payment entity_id.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The customer's user ID.
        limit (int): Maximum records to return (default 100).
        offset (int): Records to skip for pagination (default 0).
        entity_id (Optional[int]): Filter by specific payment ID (default None = all).
    
    Returns:
        List[Dict[str, Any]]: List of payment records with summary details.
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
    Retrieve customer refund summary report.
    
    Queries vw_customer_refund_summary view to get paginated refund history for a customer.
    Returns refund details including amounts, status, booking references, and processing status.
    Optionally filters by specific refund entity_id.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        user_id (int): The customer's user ID.
        limit (int): Maximum records to return (default 100).
        offset (int): Records to skip for pagination (default 0).
        entity_id (Optional[int]): Filter by specific refund ID (default None = all).
    
    Returns:
        List[Dict[str, Any]]: List of refund records with summary details.
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
    Retrieve admin booking performance analytics report.
    
    Queries vw_admin_booking_performance view to get booking metrics for admin dashboard.
    Returns performance data including occupancy rates, booking counts, revenue per booking,
    by room type and date range. Useful for business analytics and capacity planning.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        date_from (Optional[str]): Filter bookings from this date onwards (ISO format).
        date_to (Optional[str]): Filter bookings up to this date (ISO format).
        room_type (Optional[str]): Filter by specific room type (default None = all types).
        limit (int): Maximum records to return (default 500).
    
    Returns:
        List[Dict[str, Any]]: List of performance metrics including occupancy, revenue, counts.
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
    Retrieve admin revenue summary report.
    
    Queries vw_admin_revenue_summary view to get comprehensive revenue analytics.
    Returns revenue data including total income, booking revenue, refund deductions,
    revenue trends by period, and payment method breakdown.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        date_from (Optional[str]): Filter revenue from this date onwards (ISO format).
        date_to (Optional[str]): Filter revenue up to this date (ISO format).
        limit (int): Maximum records to return (default 500).
    
    Returns:
        List[Dict[str, Any]]: List of revenue summary records with financial metrics.
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
    Retrieve admin refund summary with SLA tracking.
    
    Queries vw_admin_refund_summary view to get refund analytics and SLA compliance metrics.
    Returns refund data including count, amounts, status distribution, processing time SLA,
    and refund reasons. Useful for compliance monitoring and refund performance tracking.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        limit (int): Maximum records to return (default 500).
        entity_id (Optional[int]): Filter by specific refund ID (default None = all).
    
    Returns:
        List[Dict[str, Any]]: List of refund summary records with SLA metrics.
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
    Retrieve admin payment summary report.
    
    Queries vw_admin_payment_summary view to get payment analytics including distribution
    by method, success rates, transaction volumes, and financial metrics. Useful for
    payment processing monitoring and reconciliation.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        limit (int): Maximum records to return (default 500).
    
    Returns:
        List[Dict[str, Any]]: List of payment summary records with method distribution.
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
    Retrieve admin review analytics report.
    
    Queries vw_admin_review_summary view to get review statistics including rating distribution,
    sentiment analysis, most reviewed rooms, response rates, and customer feedback trends.
    Useful for quality assurance and customer satisfaction monitoring.
    
    Args:
        db (AsyncSession): Database session for executing the query.
        limit (int): Maximum records to return (default 500).
    
    Returns:
        List[Dict[str, Any]]: List of review summary records with analytics metrics.
    """
    return await fetch_admin_review_summary(
        db=db,
        limit=limit,
    )


# ==========================================================
# 🔹 PDF EXPORT HELPER FUNCTIONS
# ==========================================================

def convert_to_pdf(data: List[Dict[str, Any]], report_title: str) -> bytes:
    """
    Convert report data to PDF format.
    
    Generates a PDF document from report data with the specified title. Uses ReportLab or
    similar library to format tabular data into a printable PDF suitable for distribution
    and record-keeping.
    
    Args:
        data (List[Dict[str, Any]]): List of report records to convert.
        report_title (str): Title to display at top of PDF document.
    
    Returns:
        bytes: PDF file content as bytes, ready for download or storage.
    """
    return generate_report_pdf(data, report_title=report_title)


async def format_report_response(
    data: List[Dict[str, Any]],
    export_pdf: bool = False,
    report_title: str = "Report"
) -> Union[Dict[str, Any], bytes]:
    """
    Format report response in JSON or PDF format.
    
    Handles report response formatting with optional PDF export. If export_pdf is True,
    converts data to PDF bytes. Otherwise returns JSON with count and items for API response.
    
    Args:
        data (List[Dict[str, Any]]): List of report records to format.
        export_pdf (bool): If True, return as PDF bytes; if False, return as JSON (default False).
        report_title (str): Title for PDF export (default "Report").
    
    Returns:
        Union[Dict[str, Any], bytes]: Either {"count": n, "items": [...]}, or PDF bytes.
    """
    if export_pdf:
        return convert_to_pdf(data, report_title)
    return {"count": len(data), "items": data}
