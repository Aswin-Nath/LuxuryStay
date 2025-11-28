from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import date

from app.database.postgres_connection import get_db
from app.dependencies.authentication import check_permission, get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.services.users import (
    list_users,
    get_user_details,
    update_user,
    update_user_status,
    check_email_availability,
    soft_delete_user,
    suspend_user,
    unsuspend_user
)
from pydantic import BaseModel, Field

# Router
users_router = APIRouter(prefix="/users", tags=["USERS"])


# ============================================================================
# Pydantic Models
# ============================================================================

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    phone_number: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role_id: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(active|suspended)$")
    dob: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Other)$")


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class SuspendUserRequest(BaseModel):
    suspend_reason: str = Field(..., min_length=5, max_length=500)


class EmailCheckResponse(BaseModel):
    available: bool
    email: str


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


# ============================================================================
# 🔹 READ - List Users with Filtering and Pagination
# ============================================================================
@users_router.get("/list", response_model=UserListResponse)
async def list_users_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role_id: Optional[int] = Query(None, description="Filter by role ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, suspended)"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort_by: str = Query("created_at", description="Column to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:READ"]),
):
    """
    List users with advanced filtering, sorting, and pagination.
    
    **Authorization:** Requires ADMIN_CREATION:READ permission.
    
    Query Parameters:
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 10, max: 100)
    - **search**: Search term for name or email
    - **role_id**: Filter by specific role
    - **status**: Filter by status (active, suspended)
    - **date_from**: Filter by creation date (from)
    - **date_to**: Filter by creation date (to)
    - **sort_by**: Column to sort by (default: created_at)
    - **sort_order**: Sort direction (asc or desc, default: desc)
    
    Returns:
        UserListResponse with users array, total count, page, and limit
    """
    result = await list_users(
        db=db,
        page=page,
        limit=limit,
        search=search,
        role_id=role_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return result


# ============================================================================
# 🔹 READ - Get User Details
# ============================================================================
@users_router.get("/{user_id}")
async def get_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:READ"]),
):
    """
    Get detailed information about a specific user.
    
    **Authorization:** Requires ADMIN_CREATION:READ permission.
    
    Args:
        user_id: User ID to fetch
    
    Returns:
        User details dictionary with all fields
    
    Raises:
        404: User not found
    """
    user_details = await get_user_details(db, user_id)
    return user_details


# ============================================================================
# 🔹 UPDATE - Update User Details
# ============================================================================
@users_router.put("/{user_id}")
async def update_user_endpoint(
    user_id: int,
    payload: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Update user details.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        user_id: User ID to update
        payload: Update request with optional fields
    
    Returns:
        Updated user details
    
    Raises:
        404: User not found
        409: Phone number already in use
    """
    updated_user = await update_user(
        db=db,
        user_id=user_id,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password=payload.password,
        role_id=payload.role_id,
        status=payload.status,
        dob=payload.dob,
        gender=payload.gender
    )
    
    await db.commit()
    
    return {
        "user_id": updated_user.user_id,
        "full_name": updated_user.full_name,
        "email": updated_user.email,
        "phone_number": updated_user.phone_number,
        "role_id": updated_user.role_id,
        "status": updated_user.status,
        "message": "User updated successfully"
    }


# ============================================================================
# 🔹 UPDATE - Update User Status
# ============================================================================
@users_router.put("/{user_id}/status")
async def update_user_status_endpoint(
    user_id: int,
    payload: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Update user status (activate, deactivate, or suspend).
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        user_id: User ID to update
        payload: Status update request
    
    Returns:
        Success message with updated status
    
    Raises:
        404: User or status not found
    """
    updated_user = await update_user_status(
        db=db,
        user_id=user_id,
        status_name=payload.status
    )
    
    await db.commit()
    
    return {
        "user_id": updated_user.user_id,
        "status": payload.status,
        "message": f"User status updated to '{payload.status}' successfully"
    }


# ============================================================================
# 🔹 READ - Check Email Availability
# ============================================================================
@users_router.get("/check-email", response_model=EmailCheckResponse)
async def check_email_endpoint(
    email: str = Query(..., description="Email to check"),
    exclude_user_id: Optional[int] = Query(None, description="User ID to exclude from check"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:READ"]),
):
    """
    Check if an email address is available for use.
    
    **Authorization:** Requires ADMIN_CREATION:READ permission.
    
    Query Parameters:
    - **email**: Email address to check
    - **exclude_user_id**: Optional user ID to exclude (for update scenarios)
    
    Returns:
        EmailCheckResponse with availability status
    """
    is_available = await check_email_availability(
        db=db,
        email=email,
        exclude_user_id=exclude_user_id
    )
    
    return EmailCheckResponse(
        available=is_available,
        email=email
    )


# ============================================================================
# 🔹 DELETE - Soft Delete User
# ============================================================================
@users_router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Soft delete a user (sets is_deleted flag).
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        user_id: User ID to delete
    
    Returns:
        Success message
    
    Raises:
        404: User not found
    """
    await soft_delete_user(db, user_id)
    await db.commit()
    
    return {
        "user_id": user_id,
        "message": "User deleted successfully"
    }


# ============================================================================
# 🔹 SUSPEND - Suspend User Account
# ============================================================================
@users_router.post("/{user_id}/suspend", status_code=status.HTTP_200_OK)
async def suspend_user_endpoint(
    user_id: int,
    payload: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Suspend a user account with a reason.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        user_id: User ID to suspend
        payload: Suspension reason (5-500 characters)
    
    Returns:
        Suspended user details
    
    Raises:
        400: Invalid suspend reason
        404: User not found
        409: User already suspended
    """
    suspended_user = await suspend_user(db, user_id, payload.suspend_reason)
    await db.commit()
    
    return {
        "user_id": suspended_user.user_id,
        "full_name": suspended_user.full_name,
        "email": suspended_user.email,
        "status": suspended_user.status,
        "suspend_reason": suspended_user.suspend_reason,
        "message": "User suspended successfully"
    }


# ============================================================================
# 🔹 UNSUSPEND - Unsuspend User Account
# ============================================================================
@users_router.post("/{user_id}/unsuspend", status_code=status.HTTP_200_OK)
async def unsuspend_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    token_payload: dict = Security(check_permission, scopes=["ADMIN_CREATION:WRITE"]),
):
    """
    Unsuspend a user account and restore it to active status.
    
    **Authorization:** Requires ADMIN_CREATION:WRITE permission.
    
    Args:
        user_id: User ID to unsuspend
    
    Returns:
        Unsuspended user details
    
    Raises:
        404: User not found
        409: User already active
    """
    unsuspended_user = await unsuspend_user(db, user_id)
    await db.commit()
    
    return {
        "user_id": unsuspended_user.user_id,
        "full_name": unsuspended_user.full_name,
        "email": unsuspended_user.email,
        "status": unsuspended_user.status,
        "suspend_reason": unsuspended_user.suspend_reason,
        "message": "User unsuspended successfully"
    }
