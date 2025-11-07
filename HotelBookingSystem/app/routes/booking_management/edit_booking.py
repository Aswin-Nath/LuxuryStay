from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.schemas.pydantic_models.booking_edits import BookingEditCreate, BookingEditResponse,ReviewPayload,DecisionPayload
from app.services.booking_service.booking_edit import (
    create_booking_edit_service,
    get_all_booking_edits_service,
    review_booking_edit_service,
    decision_on_booking_edit_service,
    change_room_status,
)
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.utils.audit_helper import log_audit

router = APIRouter(prefix="/booking-edits", tags=["BOOKING-EDITS"])


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
    obj = await create_booking_edit_service(payload, db, current_user)
    # audit booking edit create
    try:
        new_val = BookingEditResponse.model_validate(obj).model_dump()
        entity_id = f"booking_edit:{getattr(obj, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return obj


@router.get("/{booking_id}", response_model=BookingEditResponse | list[BookingEditResponse])
async def get_booking_edits(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Unified endpoint to fetch booking edits.

    - If `active=True` -> returns the active edit (or None).
    - Otherwise -> returns list of all edits for the booking.

    Authorization rules (enforced here):
    - Basic users (role_id == 1) may only access edits for bookings they own.
    - Non-basic users must have BOOKING.WRITE permission to access edits for other users.
    """
    # Authorization
    is_basic_user = getattr(current_user, "role_id", None) == 1
    if is_basic_user:
        # verify ownership by loading booking

        res = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
        booking = res.scalars().first()
        if not booking or booking.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to access this booking's edits")
    else:
        # require BOOKING.WRITE permission for non-basic users
        if not (Resources.REFUND_APPROVAL.value in user_permissions and PermissionTypes.WRITE.value in user_permissions.get(Resources.REFUND_APPROVAL.value, set())):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required to access booking edits")

    return await get_all_booking_edits_service(booking_id, db)



@router.post("/rooms/{room_id}/status")
async def change_room_status_route(
    room_id: int,
    lock: bool = Query(True, description="true to lock the room, false to unlock"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """Lock or unlock a room. Requires ROOM_MANAGEMENT.WRITE permission for non-basic users.

    - lock=True -> lock the room
    - lock=False -> unlock the room
    """
    # Permission check: only admins/managers with ROOM_MANAGEMENT.WRITE can perform this
    if not user_permissions or (
        Resources.ROOM_MANAGEMENT.value not in user_permissions
        or PermissionTypes.WRITE.value not in user_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    room = await change_room_status(db, room_id, lock)
    # Normalize enum values to strings for JSON response
    r_status = getattr(room, 'room_status', None)
    fr = getattr(room, 'freeze_reason', None)
    return {
        "ok": True,
        "room_id": room_id,
        "room_status": str(r_status),
        "freeze_reason": str(fr)
    }



# ✅ Admin Review (Suggest rooms & lock edit)
@router.post("/{edit_id}/review")
async def review_booking_edit(
    edit_id: int,
    payload: ReviewPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Admin suggests room changes and locks them for 30 minutes.
    """
    # Check admin access against canonical permission enums
    if not user_permissions or (
        Resources.ROOM_MANAGEMENT.value not in user_permissions
        or PermissionTypes.WRITE.value not in user_permissions.get(Resources.ROOM_MANAGEMENT.value, set())
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    obj = await review_booking_edit_service(edit_id, payload, db, current_user)
    # audit admin review action
    try:
        new_val = BookingEditResponse.model_validate(obj).model_dump()
        entity_id = f"booking_edit:{getattr(obj, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return obj


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
    obj = await decision_on_booking_edit_service(edit_id, payload, db, current_user)
    # audit customer decision
    try:
        new_val = BookingEditResponse.model_validate(obj).model_dump()
        entity_id = f"booking_edit:{getattr(obj, 'edit_id', None)}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=getattr(current_user, 'user_id', None), user_id=getattr(current_user, 'user_id', None))
    except Exception:
        pass
    return obj