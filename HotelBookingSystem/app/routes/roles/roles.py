from fastapi import APIRouter,status,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.postgres.roles import RoleCreate, RoleResponse     # your Pydantic schemas
from app.models.orm.roles import Roles                     # your ORM model
from typing import List
roles_router=APIRouter(prefix="/roles",tags=["ROLES"])

@roles_router.post("/",response_model=RoleResponse)
async def create_new_role(payload:RoleCreate,db:AsyncSession=Depends(get_db)):
     # Check for existing role
    result = await db.execute(select(Roles).where(Roles.role_name == payload.role_name))
    existing_role = result.scalars().first()

    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{payload.role_name}' already exists."
        )

    # Create new role instance
    role_obj = Roles(**payload.model_dump())

    db.add(role_obj)
    await db.commit()
    await db.refresh(role_obj)

    schema_data = RoleResponse.model_validate(role_obj)
    schema_data = schema_data.model_copy(update={"message": "Role created successfully"})
    return schema_data



@roles_router.get("/", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    """Fetch all roles. Useful for admin dashboards and role-permission mapping."""
    result = await db.execute(select(Roles))
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in roles]


