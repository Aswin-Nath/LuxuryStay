from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.refunds import RefundCreate, RefundResponse
from app.schemas.pydantic_models.booking import BookingCreate, BookingResponse
from app.services.booking_service.bookings_service import create_booking as svc_create_booking, get_booking as svc_get_booking, list_bookings as svc_list_bookings, query_bookings as svc_query_bookings
from app.models.sqlalchemy_schemas.users import Users
from app.dependencies.authentication import get_current_user, get_user_permissions
from app.models.sqlalchemy_schemas.permissions import Resources, PermissionTypes
from app.core.exceptions import ForbiddenError
from app.services.refunds_service.refunds_service import cancel_booking_and_create_refund as svc_cancel_booking
from app.core.cache import get_cached, set_cached, invalidate_pattern


router = APIRouter(prefix="/api/bookings", tags=["BOOKINGS"])



@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(payload: BookingCreate, db: AsyncSession = Depends(get_db), user_permissions: dict = Depends(get_user_permissions), current_user: Users = Depends(get_current_user)):
	# Permission check: require BOOKING.WRITE
	if not (
		Resources.BOOKING.value in user_permissions
		and PermissionTypes.WRITE.value in user_permissions[Resources.BOOKING.value]
	):
		raise ForbiddenError("Insufficient permissions to create bookings")

	# Use authenticated user as the booking user if they didn't supply or to enforce ownership
	if payload.user_id != current_user.user_id:
		# Prefer using current_user to avoid spoofing
		payload.user_id = current_user.user_id

	obj = await svc_create_booking(db, payload)
	# invalidate bookings cache after new booking
	await invalidate_pattern("bookings:*")
	return BookingResponse.model_validate(obj).model_dump(exclude={"created_at"})

@router.post("/{booking_id}/cancel", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def cancel_booking(booking_id: int, payload: RefundCreate, db: AsyncSession = Depends(get_db), current_user: Users = Depends(get_current_user)):
    obj = await svc_cancel_booking(db, booking_id, payload, current_user)
    return RefundResponse.model_validate(obj)


@router.get("/", response_model=List[BookingResponse])
async def list_all_bookings(limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
	cache_key = f"bookings:limit:{limit}:offset:{offset}"
	cached = await get_cached(cache_key)
	if cached is not None:
		return cached

	items = await svc_list_bookings(db, limit=limit, offset=offset)
	result = [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]
	await set_cached(cache_key, result, ttl=120)
	return result


@router.get("/query", response_model=List[BookingResponse])
async def bookings_query(user_id: Optional[int] = None, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
	cache_key = f"bookings:query:user:{user_id}:status:{status}"
	cached = await get_cached(cache_key)
	if cached is not None:
		return cached

	items = await svc_query_bookings(db, user_id=user_id, status=status)
	result = [BookingResponse.model_validate(i).model_dump(exclude={"created_at"}) for i in items]
	await set_cached(cache_key, result, ttl=60)
	return result


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
	obj = await svc_get_booking(db, booking_id)
	return BookingResponse.model_validate(obj).model_dump(exclude={"created_at"})

