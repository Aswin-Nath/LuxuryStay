from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.sqlalchemy_schemas.roles import Roles


async def create_role(db: AsyncSession, payload) -> Roles:
    result = await db.execute(select(Roles).where(Roles.role_name == payload.role_name))
    existing_role = result.scalars().first()

    if existing_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role '{payload.role_name}' already exists.")

    role_obj = Roles(**payload.model_dump())
    db.add(role_obj)
    await db.commit()
    await db.refresh(role_obj)
    return role_obj


async def list_roles(db: AsyncSession) -> List[Roles]:
    result = await db.execute(select(Roles))
    roles = result.scalars().all()
    return roles
