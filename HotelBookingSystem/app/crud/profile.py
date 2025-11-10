from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sqlalchemy_schemas.users import Users


# ==========================================================
# 🔹 READ PROFILE
# ==========================================================

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Users]:
    """Fetch user profile by ID."""
    stmt = select(Users).where(Users.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


# ==========================================================
# 🔹 UPDATE PROFILE
# ==========================================================

async def update_user_profile(db: AsyncSession, user: Users, updates: dict) -> Users:
    """Update scalar fields in user profile."""
    for k, v in updates.items():
        if hasattr(user, k):
            setattr(user, k, v)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ==========================================================
# 🔹 UPDATE PROFILE IMAGE
# ==========================================================

async def update_user_profile_image(db: AsyncSession, user: Users, image_url: str) -> Users:
    """Set profile image URL."""
    user.profile_image_url = image_url
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ==========================================================
# 🔹 UPDATE PASSWORD
# ==========================================================

async def update_user_password(db: AsyncSession, user: Users, hashed_password: str) -> Users:
    """Change user password."""
    user.password = hashed_password
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
