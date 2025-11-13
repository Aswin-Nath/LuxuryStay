from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    Security,
    status,
    Query,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ==========================================================
# 🧩 Core Imports
# ==========================================================
from app.database.postgres_connection import get_db
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.bookings import Bookings
from app.dependencies.authentication import get_current_user, check_permission
from app.core.cache import get_cached, set_cached, invalidate_pattern
from app.core.exceptions import ForbiddenException
from app.utils.audit_util import log_audit

# ==========================================================
# 🧱 Schemas
# ==========================================================
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.schemas.pydantic_models.refunds import RefundCreate, RefundResponse
from app.schemas.pydantic_models.booking_edits import (
    BookingEditCreate,
    BookingEditResponse,
    UpdateRoomOccupancyRequest,
)
from app.schemas.pydantic_models.reviews import ReviewCreate
# ==========================================================
# ⚙️ Services
# ==========================================================
from app.services.bookings_service import (
    create_booking as svc_create_booking,
    get_booking as svc_get_booking,
    list_bookings as svc_list_bookings,
    query_bookings as svc_query_bookings,
)
from app.services.refunds_service import (
    cancel_booking_and_create_refund as svc_cancel_booking,
)
from app.services.booking_edit import (
    create_booking_edit_service,
    get_all_booking_edits_service,
    update_room_occupancy_service,
)

# ==========================================================
# 📦 Router Definition
# ==========================================================
router = APIRouter(prefix="/bookings", tags=["BOOKINGS"])


# ==========================================================
# 🔹 CREATE - Create a new booking
# ==========================================================
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
    current_user: Users = Depends(get_current_user),
):
    booking_record = await svc_create_booking(db, payload, user_id=current_user.user_id)

    try:
        new_val = BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})
        entity_id = f"booking:{booking_record.booking_id}"
        await log_audit(entity="booking", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass

    await invalidate_pattern("bookings:*")
    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ==========================================================
# 🔹 UPDATE - Cancel booking & create refund
# ==========================================================
@router.post("/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    refund_record = await svc_cancel_booking(db, booking_id, current_user)

    try:
        new_val = RefundResponse.model_validate(refund_record).model_dump()
        entity_id = f"booking:{booking_id}"
        await log_audit(entity="booking", entity_id=entity_id, action="UPDATE", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass

    await invalidate_pattern("bookings:*")
    await invalidate_pattern("refunds:*")
    return RefundResponse.model_validate(refund_record)


# ==========================================================
# 🔹 READ - Customer: Get own booking by ID
# ==========================================================
@router.get("/customer/{booking_id}", response_model=BookingResponse)
async def get_customer_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    booking_record = await svc_get_booking(db, booking_id)
    if booking_record.user_id != current_user.user_id:
        raise ForbiddenException("You don't have permission to access this booking")

    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ==========================================================
# 🔹 READ - Admin: Get booking by ID
# ==========================================================
@router.get("/admin/{booking_id}", response_model=BookingResponse)
async def get_admin_booking_by_id(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    booking_record = await svc_get_booking(db, booking_id)
    return BookingResponse.model_validate(booking_record).model_dump(exclude={"created_at"})


# ==========================================================
# 🔹 READ - Customer: List own bookings
# ==========================================================
@router.get("/customer", response_model=List[BookingResponse])
async def get_customer_bookings(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "CUSTOMER"]),
):
    items = await svc_query_bookings(db, user_id=current_user.user_id, status=status)
    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


# ==========================================================
# 🔹 READ - Admin: List all bookings (filterable)
# ==========================================================
@router.get("/admin", response_model=List[BookingResponse])
async def get_admin_bookings(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:READ", "ADMIN"]),
):
    if status:
        items = await svc_query_bookings(db, user_id=None, status=status)
    else:
        items = await svc_list_bookings(db, limit=limit, offset=offset)

    return [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]


# ==========================================================
# 🧩 BOOKING EDITS SECTION
# ==========================================================
@router.post("/edits", response_model=BookingEditResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_edit(
    payload: BookingEditCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    booking_edit_record = await create_booking_edit_service(payload, db, current_user)

    try:
        new_val = BookingEditResponse.model_validate(booking_edit_record).model_dump()
        entity_id = f"booking_edit:{booking_edit_record.edit_id}"
        await log_audit(entity="booking_edit", entity_id=entity_id, action="INSERT", new_value=new_val, changed_by_user_id=current_user.user_id, user_id=current_user.user_id)
    except Exception:
        pass

    return booking_edit_record


@router.get("/{booking_id}/edits", response_model=List[BookingEditResponse])
async def get_booking_edits(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE"]),
):
    query_result = await db.execute(select(Bookings).where(Bookings.booking_id == booking_id))
    booking = query_result.scalars().first()

    if not booking or booking.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to access this booking's edits")

    return await get_all_booking_edits_service(booking_id, db)



# ==========================================================
# 🔹 PATCH - Update room occupancy (adults/children)
# ==========================================================
@router.patch("/{booking_id}/occupancy", status_code=status.HTTP_200_OK)
async def update_occupancy(
    booking_id: int,
    payload: UpdateRoomOccupancyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["BOOKING:WRITE", "CUSTOMER"]),
):
    updated_rooms = await update_room_occupancy_service(
        booking_id=booking_id,
        room_occupancy_updates=payload.model_dump(),
        db=db,
        current_user=current_user,
    )

    try:
        entity_id = f"booking_room_maps:{booking_id}"
        new_val = {
            "booking_id": booking_id,
            "rooms": [
                {
                    "room_id": room.room_id,
                    "room_type_id": room.room_type_id,
                    "adults": room.adults,
                    "children": room.children,
                }
                for room in updated_rooms
            ],
        }
        await log_audit(
            entity="booking_occupancy",
            entity_id=entity_id,
            action="UPDATE",
            new_value=new_val,
            changed_by_user_id=current_user.user_id,
            user_id=current_user.user_id,
        )
    except Exception:
        pass

    return {
        "booking_id": booking_id,
        "rooms": [
            {
                "room_id": room.room_id,
                "room_type_id": room.room_type_id,
                "adults": room.adults,
                "children": room.children,
                "is_room_active": room.is_room_active,
            }
            for room in updated_rooms
        ],
    }
