import hashlib
import secrets
from datetime import datetime, timedelta
from jose import jwt
from app.models.orm.users import Users
from app.models.orm.authentication import Sessions
import os

# Load JWT configs from .env
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


def _hash_password(plain: str) -> str:
    """Hash a password using PBKDF2-HMAC and return salt$hexhash"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def _verify_password(stored: str, plain: str) -> bool:
    try:
        salt, hexhash = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return dk.hex() == hexhash


# =====================================================
# 🔐 JWT TOKEN GENERATION
# =====================================================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "scope": "refresh_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


# =====================================================
# 👤 USER CREATION
# =====================================================
async def create_user(db, *, full_name: str, email: str, password: str, phone_number: str | None, role_id: int, status_id: int,created_by:int):
    hashed = _hash_password(password)
    user_obj = Users(
        full_name=full_name,
        email=email,
        hashed_password=hashed,
        phone_number=phone_number,
        role_id=role_id,
        status_id=status_id,
        created_by=created_by
    )
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)
    return user_obj


# =====================================================
# 🧾 AUTHENTICATION (LOGIN)
# =====================================================
async def authenticate_user(db, *, email: str, password: str):
    from sqlalchemy import select
    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not _verify_password(user.hashed_password, password):
        return None
    return user


# =====================================================
# 🪪 SESSION CREATION (JWT-ONLY)
# =====================================================
async def create_session(db, user, device_info: str | None = None, ip: str | None = None):
    access_token, access_exp = create_access_token({"sub": str(user.user_id)})
    refresh_token, refresh_exp = create_refresh_token({"sub": str(user.user_id)})

    session = Sessions(
        user_id=user.user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_exp,
        refresh_token_expires_at=refresh_exp,
        device_info=device_info,
        ip_address=ip,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
