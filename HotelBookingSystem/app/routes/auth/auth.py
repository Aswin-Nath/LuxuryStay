from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import get_db
from app.models.orm.users import Users
from app.models.orm.roles import Roles
from app.models.orm.authentication import Sessions
from app.models.postgres.users import UserCreate, LoginRequest, UserResponse, TokenResponse
from app.services.auth import create_user, authenticate_user, create_session
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies.authentication import get_current_user,get_user_permissions
auth_router = APIRouter(prefix="/auth", tags=["AUTH"])
from app.models.orm.permissions import Resources, PermissionTypes


@auth_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Enforce only normal user role can signup (not admin)
    # The system's 'user' role id is 1 per DB note; if client supplies different role, reject
    if payload.role_id is not None and payload.role_id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create admin users via this endpoint")

    # check existing email
    result = await db.execute(select(Users).where(Users.email == payload.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user_obj = await create_user(db, full_name=payload.full_name, email=payload.email, password=payload.password, phone_number=payload.phone_number, role_id=1,status_id=1)

    return UserResponse.model_validate(user_obj)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 Login endpoint that returns JWT tokens on successful authentication.
    """
    # Authenticate user by email/username
    user = await authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create a session + tokens
    session = await create_session(
        db,
        user,
        device_info=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    expires_in = (
        int((session.access_token_expires_at - session.login_time).total_seconds())
        if session.access_token_expires_at and session.login_time
        else 3600
    )

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=expires_in,
        token_type="Bearer",
        role_id=user.role_id
    )

@auth_router.post("/admin/create", status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Admin creation endpoint restricted by permission map.
    """

    # Permission check
    allowed = "ADMIN" in user_permissions and "WRITE" in user_permissions["ADMIN"]
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create admin users",
        )

    # Continue logic to create admin
    user_obj = await create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=payload.role_id,
        status_id=1,
    )

    return UserResponse.model_validate(user_obj)

# ==============================================================
# 🧠 SUPER ADMIN CREATION (Permission-Protected)
# ==============================================================
@auth_router.post("/super-admin/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_super_admin(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    user_permissions: dict = Depends(get_user_permissions),
):
    """
    Endpoint to create Super Admin users.
    Requires `Super_Admin_Creation` resource with `WRITE` permission.
    """

    # ----------------------------------------------------------
    # 🔐 Permission Check
    # ----------------------------------------------------------
    print("THIS",user_permissions)
    allowed = (
        Resources.Super_Admin_Creation in user_permissions
        and PermissionTypes.WRITE in user_permissions[Resources.Super_Admin_Creation]
        )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create Super Admins",
        )

    # ----------------------------------------------------------
    # 🧭 Email Conflict Check
    # ----------------------------------------------------------
    existing_email_query = await db.execute(select(Users).where(Users.email == payload.email))
    if existing_email_query.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # ----------------------------------------------------------
    # 🧱 Create Super Admin
    # ----------------------------------------------------------
    user_obj = await create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        phone_number=payload.phone_number,
        role_id=6,  # Super Admin Role ID
        status_id=1,
    )

    return UserResponse.model_validate(user_obj)
