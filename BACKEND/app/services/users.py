from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.roles import Roles
from app.crud.authentication import get_user_by_id, get_user_by_email


async def list_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """
    List users with filtering, sorting, and pagination.
    
    Args:
        db: Database session
        page: Page number (1-indexed)
        limit: Items per page
        search: Search term for name/email
        role_id: Filter by role ID
        status: Filter by status ('active' or 'suspended')
        date_from: Filter by created date (from)
        date_to: Filter by created date (to)
        sort_by: Column to sort by
        sort_order: Sort direction (asc/desc)
    
    Returns:
        Dictionary with users list, total count, page, and limit
    """
    # Base query with relationships - exclude customer role (role_id=1)
    query = select(Users).options(
        joinedload(Users.role)
    ).where(
        and_(
            Users.is_deleted == False,
            Users.role_id != 1  # Exclude customers
        )
    )
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Users.full_name.ilike(search_term),
                Users.email.ilike(search_term)
            )
        )
    
    if role_id:
        query = query.where(Users.role_id == role_id)
    
    if status:
        # Filter by status field (now direct string comparison)
        valid_statuses = ["active", "suspended"]
        if status.lower() in valid_statuses:
            query = query.where(
                func.lower(Users.status) == status.lower()
            )
    
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.where(Users.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.where(Users.created_at <= to_date)
        except ValueError:
            pass
    
    # Count total items (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_column = getattr(Users, sort_by, Users.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().unique().all()
    
    # Format response
    users_list = []
    for user in users:
        user_dict = {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role_id": user.role_id,
            "role_name": user.role.role_name if user.role else None,
            "status": user.status,
            "suspend_reason": user.suspend_reason,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "dob": user.dob.isoformat() if user.dob else None,
            "gender": user.gender.value if user.gender else None,
            "profile_image_url": user.profile_image_url,
        }
        users_list.append(user_dict)
    
    return {
        "users": users_list,
        "total": total,
        "page": page,
        "limit": limit
    }


async def get_user_details(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific user.
    
    Args:
        db: Database session
        user_id: User ID to fetch
    
    Returns:
        User details dictionary
    
    Raises:
        HTTPException: If user not found
    """
    query = select(Users).options(
        joinedload(Users.role),
        joinedload(Users.status)
    ).where(
        Users.user_id == user_id,
        Users.is_deleted == False
    )
    
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role_id": user.role_id,
        "role_name": user.role.role_name if user.role else None,
        "status": user.status,
        "suspend_reason": user.suspend_reason,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "dob": user.dob.isoformat() if user.dob else None,
        "gender": user.gender.value if user.gender else None,
        "profile_image_url": user.profile_image_url,
        "loyalty_points": user.loyalty_points,
        "created_by": user.created_by,
    }


async def update_user(
    db: AsyncSession,
    user_id: int,
    full_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    password: Optional[str] = None,
    role_id: Optional[int] = None,
    status: Optional[str] = None,
    dob: Optional[date] = None,
    gender: Optional[str] = None,
) -> Users:
    """
    Update user details.
    
    Args:
        db: Database session
        user_id: User ID to update
        full_name: New full name
        phone_number: New phone number
        password: New password (optional, will be hashed if provided)
        role_id: New role ID
        status: New status ('active' or 'suspended')
        dob: New date of birth
        gender: New gender
    
    Returns:
        Updated user object
    
    Raises:
        HTTPException: If user not found or validation fails
    """
    user = await get_user_by_id(db, user_id)
    
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if full_name is not None:
        user.full_name = full_name
    
    if phone_number is not None:
        # Check if phone number is already taken by another user
        existing = await db.execute(
            select(Users).where(
                Users.phone_number == phone_number,
                Users.user_id != user_id,
                Users.is_deleted == False
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already in use"
            )
        user.phone_number = phone_number
    
    if password is not None:
        # Hash the new password
        from app.utils.authentication_util import hash_password
        user.password_hash = hash_password(password)
    
    if role_id is not None:
        # Verify role exists
        role_check = await db.execute(select(Roles).where(Roles.role_id == role_id))
        if not role_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        user.role_id = role_id
    
    if status is not None:
        # Validate status value
        valid_statuses = ["active", "suspended"]
        if status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed values: {', '.join(valid_statuses)}"
            )
        user.status = status.lower()
    
    if dob is not None:
        user.dob = dob
    
    if gender is not None:
        from app.models.sqlalchemy_schemas.users import GenderTypes
        try:
            user.gender = GenderTypes[gender.title()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid gender value. Must be Male, Female, or Other"
            )
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


async def update_user_status(
    db: AsyncSession,
    user_id: int,
    status_name: str
) -> Users:
    """
    Update user status with validation.
    
    Args:
        db: Database session
        user_id: User ID to update
        status_name: New status (must be 'active' or 'suspended')
    
    Returns:
        Updated user object
    
    Raises:
        HTTPException: If user not found or invalid status
    """
    # Validate status value
    valid_statuses = ["active", "suspended"]
    if status_name.lower() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed values: {', '.join(valid_statuses)}"
        )
    
    user = await get_user_by_id(db, user_id)
    
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update status directly (now it's a string field, not FK)
    user.status = status_name.lower()
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


async def check_email_availability(
    db: AsyncSession,
    email: str,
    exclude_user_id: Optional[int] = None
) -> bool:
    """
    Check if email is available for use.
    
    Args:
        db: Database session
        email: Email to check
        exclude_user_id: User ID to exclude from check (for updates)
    
    Returns:
        True if email is available, False otherwise
    """
    query = select(Users).where(
        Users.email == email,
        Users.is_deleted == False
    )
    
    if exclude_user_id:
        query = query.where(Users.user_id != exclude_user_id)
    
    result = await db.execute(query)
    existing_user = result.scalars().first()
    
    return existing_user is None


async def soft_delete_user(db: AsyncSession, user_id: int) -> Users:
    """
    Soft delete a user (set is_deleted flag).
    
    Args:
        db: Database session
        user_id: User ID to delete
    
    Returns:
        Deleted user object
    
    Raises:
        HTTPException: If user not found
    """
    user = await get_user_by_id(db, user_id)
    
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_deleted = True
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


async def suspend_user(
    db: AsyncSession,
    user_id: int,
    suspend_reason: str,
) -> Users:
    """
    Suspend a user account with a reason.
    
    Args:
        db: Database session
        user_id: User ID to suspend
        suspend_reason: Reason for suspension (max 500 chars)
    
    Returns:
        Suspended user object
    
    Raises:
        HTTPException: If user not found or invalid reason
    """
    # Validate suspend_reason length
    if not suspend_reason or len(suspend_reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspend reason is required and cannot be empty"
        )
    
    if len(suspend_reason) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspend reason must be 500 characters or less"
        )
    
    user = await get_user_by_id(db, user_id)
    
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already suspended"
        )
    
    # Update user status and suspend reason
    user.status = "suspended"
    user.suspend_reason = suspend_reason.strip()
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


async def unsuspend_user(
    db: AsyncSession,
    user_id: int,
) -> Users:
    """
    Unsuspend a user account and clear the suspend reason.
    
    Args:
        db: Database session
        user_id: User ID to unsuspend
    
    Returns:
        Unsuspended user object
    
    Raises:
        HTTPException: If user not found or already active
    """
    user = await get_user_by_id(db, user_id)
    
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already active"
        )
    
    # Update user status and clear suspend reason
    user.status = "active"
    user.suspend_reason = None
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user
