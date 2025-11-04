from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.pydantic_models.booking_edits import BookingEditCreate, BookingEditResponse,ReviewPayload,DecisionPayload
from app.services.booking_service.booking_edit import (
    create_booking_edit_service,
    get_active_booking_edit_service,
    get_all_booking_edits_service,
    review_booking_edit_service,
    decision_on_booking_edit_service
)

router = APIRouter(prefix="/booking-edits", tags=["booking-edits"])


# ✅ 1️⃣ Create Booking Edit
@router.post("/", response_model=BookingEditResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_edit(
    payload: BookingEditCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a booking edit request (customer initiated).
    """
    return await create_booking_edit_service(payload, db, current_user)


# ✅ 2️⃣ Get Active Booking Edit
@router.get("/active", response_model=BookingEditResponse | None)
async def get_active_booking_edit(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Fetch active edit for a booking.
    Returns None if no edit is active (PENDING or AWAITING_CUSTOMER_RESPONSE).
    """
    return await get_active_booking_edit_service(booking_id, db)


# ✅ 3️⃣ Get All Edits for a Booking
@router.get("/{booking_id}", response_model=list[BookingEditResponse])
async def get_all_booking_edits(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve all edits linked to a specific booking.
    """
    return await get_all_booking_edits_service(booking_id, db)

# ✅ Admin Review (Suggest rooms & lock edit)
@router.post("/{edit_id}/review")
async def review_booking_edit(
    edit_id: int,
    payload: ReviewPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    perms=Depends(get_user_permissions),
):
    """
    Admin suggests room changes and locks them for 30 minutes.
    """
    # Check admin access
    if not perms or ("ROOM_MANAGEMENT" not in perms or "WRITE" not in perms.get("ROOM_MANAGEMENT", set())):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    return await review_booking_edit_service(edit_id, payload, db, current_user)


# ✅ Customer Decision (Accept or Reject)
@router.post("/{edit_id}/decision")
async def decision_booking_edit(
    edit_id: int,
    payload: DecisionPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Customer accepts or rejects the admin-proposed edit.
    """
    return await decision_on_booking_edit_service(edit_id, payload, db, current_user)