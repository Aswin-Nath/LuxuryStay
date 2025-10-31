from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.pydantic_models.roles import RoleCreate, RoleResponse
from typing import List
from app.services.roles_service import create_role as svc_create_role, list_roles as svc_list_roles

roles_router = APIRouter(prefix="/roles", tags=["ROLES"])


@roles_router.post("/", response_model=RoleResponse)
async def create_new_role(payload: RoleCreate, db: AsyncSession = Depends(get_db)):
    role_obj = await svc_create_role(db, payload)
    schema_data = RoleResponse.model_validate(role_obj)
    return schema_data.model_copy(update={"message": "Role created successfully"})


@roles_router.get("/", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = await svc_list_roles(db)
    return [RoleResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in roles]



