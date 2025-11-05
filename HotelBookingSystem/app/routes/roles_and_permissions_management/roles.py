from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.schemas.pydantic_models.roles import RoleCreate, RoleResponse
from typing import List
from app.services.roles_and_permissions_service.roles_service import create_role as svc_create_role, list_roles as svc_list_roles
from app.dependencies.authentication import get_user_permissions, ensure_not_basic_user
from app.core.cache import get_cached, set_cached, invalidate_pattern

roles_router = APIRouter(prefix="/roles", tags=["ROLES"])


@roles_router.post("/", response_model=RoleResponse)
async def create_new_role(payload: RoleCreate, db: AsyncSession = Depends(get_db),
                          _ok: bool = Depends(ensure_not_basic_user),
                          user_perms: dict = Depends(get_user_permissions)):
    # Require ADMIN_CREATION:READ permission to access roles endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")
    role_obj = await svc_create_role(db, payload)
    # Invalidate roles cache after creation
    await invalidate_pattern("roles:*")
    schema_data = RoleResponse.model_validate(role_obj)
    return schema_data.model_copy(update={"message": "Role created successfully"})


@roles_router.get("/", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db), _ok: bool = Depends(ensure_not_basic_user), user_perms: dict = Depends(get_user_permissions)):
    # Require ADMIN_CREATION:READ permission to access roles endpoints
    if not user_perms or "ADMIN_CREATION" not in user_perms or "READ" not in user_perms.get("ADMIN_CREATION", set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges: ADMIN_CREATION:READ required")
    cache_key = "roles:all"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    roles = await svc_list_roles(db)
    result = [RoleResponse.model_validate(r).model_copy(update={"message": "Fetched successfully"}) for r in roles]
    await set_cached(cache_key, result, ttl=300)
    return result

