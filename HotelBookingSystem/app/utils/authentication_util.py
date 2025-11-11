import hashlib
import secrets
from datetime import datetime, timedelta
from jose import jwt
import uuid
from app.models.sqlalchemy_schemas.users import Users
from app.models.sqlalchemy_schemas.authentication import Sessions
from app.models.sqlalchemy_schemas.authentication import Verifications, VerificationType
from app.models.sqlalchemy_schemas.authentication import BlacklistedTokens, TokenType, RevokedType
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import logging
import traceback
from jose import jwt, JWTError
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid
import re
from app.core.redis_manager import redis
from typing import Optional, Tuple
load_dotenv()
_logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))


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
def create_access_token(data: dict, expires_delta: timedelta | None = None, jti: str | None = None):
    """Create an access JWT. Optionally include a `jti` claim."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    if jti:
        to_encode.update({"jti": str(jti)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def create_refresh_token(data: dict, expires_delta: timedelta | None = None, jti: str | None = None):
    """Create a refresh JWT. Optionally include a `jti` claim."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "scope": "refresh_token"})
    if jti:
        to_encode.update({"jti": str(jti)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


# =====================================================
# 👤 USER CREATION
# =====================================================
async def create_user(db, *, full_name: str, email: str, password: str, phone_number: str | None, role_id: int, status_id: int,created_by:int):
    hashed = _hash_password(password)
    user_record = Users(
        full_name=full_name,
        email=email,
        hashed_password=hashed,
        phone_number=phone_number,
        role_id=role_id,
        status_id=status_id,
        created_by=created_by
    )
    db.add(user_record)
    await db.commit()
    await db.refresh(user_record)
    return user_record


# =====================================================
# 🧾 AUTHENTICATION (LOGIN)
# =====================================================
async def authenticate_user(db, *, email: str, password: str):
    from sqlalchemy import select
    query_result = await db.execute(select(Users).where(Users.email == email))
    user = query_result.scalars().first()
    if not user:
        return None
    if not _verify_password(user.hashed_password, password):
        return None
    return user


# =====================================================
# 🪪 SESSION CREATION (JWT-ONLY)
# =====================================================
async def create_session(db, user, device_info: str, ip: str):
    # create a unique jti for this session and include it in both tokens
    session_jti = uuid.uuid4()
    access_token, access_exp = create_access_token({"sub": str(user.user_id)}, jti=str(session_jti))
    refresh_token, refresh_exp = create_refresh_token({"sub": str(user.user_id)}, jti=str(session_jti))

    session = Sessions(
        session_id=None,
        jti=session_jti,
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


# =====================================================
# 🔑 VERIFICATION / OTP HELPERS
# =====================================================
def _generate_otp(digits: int = 6) -> str:
    return f"{secrets.randbelow(10 ** digits):0{digits}d}"

async def create_verification(db: AsyncSession, user_id: int, verification_type: VerificationType, ip: str | None = None, expires_minutes: int = 10):
    """Create a verification/OTP record and (optionally) return the otp so caller can send it.

    NOTE: returning the OTP is useful for dev environments where SMTP isn't configured.
    """
    otp = _generate_otp(6)
    expires = datetime.utcnow() + timedelta(minutes=expires_minutes)
    v = Verifications(
        user_id=user_id,
        verification_type=verification_type,
        otp_code=otp,
        expires_at=expires,
        ip_address=ip,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


async def verify_otp(db: AsyncSession, user_id: int, otp: str, verification_type: VerificationType, max_attempts: int = 5):
    """Verify an OTP for a user. Returns (True, verification_obj) on success, (False, reason) on failure.
    Marks record as verified when successful.
    """
    query_result = await db.execute(
        select(Verifications).where(
            Verifications.user_id == user_id,
            Verifications.verification_type == verification_type,
        ).order_by(Verifications.created_at.desc())
    )
    verification_record = query_result.scalars().first()
    if not verification_record:
        return False, "No verification found"
    # check expiration
    if verification_record.expires_at and datetime.utcnow() > verification_record.expires_at:
        return False, "OTP expired"
    # check attempts
    if verification_record.attempt_count >= max_attempts:
        return False, "Max attempts exceeded"
    # verify
    if verification_record.otp_code != otp:
        # increment attempt_count
        await db.execute(
            update(Verifications)
            .where(Verifications.verification_id == verification_record.verification_id)
            .values(attempt_count=Verifications.attempt_count + 1)
        )
        await db.commit()
        return False, "Invalid OTP"

    # success: mark verified
    await db.execute(
        update(Verifications)
        .where(Verifications.verification_id == verification_record.verification_id)
        .values(is_verified=True, verified_at=datetime.utcnow())
    )
    await db.commit()
    return True, verification_record


async def update_user_password(db: AsyncSession, user: Users, new_password: str):
    """Hash and update the user's password."""
    hashed = _hash_password(new_password)
    await db.execute(
        update(Users)
        .where(Users.user_id == user.user_id)
        .values(hashed_password=hashed, last_password_updated=datetime.utcnow())
    )
    await db.commit()
    # refresh user object
    await db.refresh(user)
    return user


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a simple plain-text email using SMTP env configuration.

    Returns True on success, False if SMTP isn't configured or send failed.
    This function is defensive and logs detailed errors to help debugging.
    """
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT_RAW = os.getenv("SMTP_PORT")
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    SMTP_FROM = os.getenv("SMTP_FROM")
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")

    # parse port safely
    smtp_port = None
    try:
        if SMTP_PORT_RAW:
            smtp_port = int(SMTP_PORT_RAW)
    except Exception:
        _logger.warning("Invalid SMTP_PORT value: %s", SMTP_PORT_RAW)

    if not SMTP_HOST or not smtp_port:
        _logger.warning("SMTP not configured (HOST=%s, PORT=%s). Email to %s will not be sent.", SMTP_HOST, SMTP_PORT_RAW, to_email)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)
    try:
        if SMTP_USE_SSL or smtp_port == 465:
            # implicit SSL
            with smtplib.SMTP_SSL(SMTP_HOST, smtp_port, timeout=15) as s:
                if SMTP_USER and SMTP_PASS:
                    s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, smtp_port, timeout=15) as s:
                s.ehlo()
                s.starttls()
                s.ehlo()
                if SMTP_USER and SMTP_PASS:
                    s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)

        _logger.info("Email sent to %s (subject=%s)", to_email, subject)
        return True
    except smtplib.SMTPAuthenticationError as e:
        _logger.error("SMTP authentication failed for user %s: %s", SMTP_USER, e)
        _logger.debug(traceback.format_exc())
        return False
    except Exception as e:
        _logger.error("Failed to send email to %s: %s", to_email, e)
        _logger.debug(traceback.format_exc())
        return False


# =====================================================
# 🛡 TOKEN BLACKLIST / SESSION REVOCATION HELPERS
# =====================================================
def _hash_token(value: str) -> str:
    """Return a SHA-256 hex digest of the token value for storage in blacklist."""
    return hashlib.sha256(value.encode()).hexdigest()


async def blacklist_token(db: AsyncSession, *, user_id: int, session_id, token_value: str, token_type: TokenType, reason: str | None = None, revoked_type: RevokedType = RevokedType.MANUAL_REVOKED):
    """Store a hashed token in BlacklistedTokens table."""
    h = _hash_token(token_value)
    bt = BlacklistedTokens(
        user_id=user_id,
        session_id=session_id,
        token_type=token_type,
        token_value_hash=h,
        revoked_type=revoked_type,
        reason=reason,
    )
    db.add(bt)
    await db.commit()
    await db.refresh(bt)
    return bt


async def revoke_session(db: AsyncSession, *, session: Sessions, reason: str | None = None):
    """Revoke a session: blacklist its access and refresh tokens and mark session inactive.

    This will create BlacklistedTokens entries for both tokens and update the session row.
    """
    # Blacklist access token
    try:
        await blacklist_token(
            db,
            user_id=session.user_id,
            session_id=session.session_id,
            token_value=session.access_token,
            token_type=TokenType.ACCESS,
            reason=reason,
            revoked_type=RevokedType.MANUAL_REVOKED,
        )
    except Exception:
        # best-effort; continue
        pass

    # Blacklist refresh token
    try:
        await blacklist_token(
            db,
            user_id=session.user_id,
            session_id=session.session_id,
            token_value=session.refresh_token,
            token_type=TokenType.REFRESH,
            reason=reason,
            revoked_type=RevokedType.MANUAL_REVOKED,
        )
    except Exception:
        pass

    # mark session as inactive
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = reason
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session



async def refresh_access_token(db: AsyncSession, access_token_value: str):
    """
    Complete token rotation:
    - Validate refresh token
    - Verify session + expiry
    - Rotate access token, refresh token, and JTI for better security
    - Return updated session with all new tokens
    """

    # Step 1: Decode access token and extract user
    try:
        payload = jwt.decode(access_token_value, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise Exception("Invalid access_token")

    # Step 2: Find session linked to this access token
    result = await db.execute(
        select(Sessions).where(Sessions.access_token == access_token_value)
    )
    session = result.scalars().first()
    if not session or not session.is_active:
        raise Exception("Invalid or inactive session")

    # Step 3: Check refresh token expiry
    if session.refresh_token_expires_at and datetime.utcnow() > session.refresh_token_expires_at:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        db.add(session)
        await db.commit()
        raise Exception("Refresh token expired")

    # Step 4: Generate new JTI for the rotated session
    new_jti = uuid.uuid4()
    
    # Step 5: Rotate (overwrite) the access token with new JTI
    new_access_token, new_access_exp = create_access_token(
        {"sub": str(user_id), "scope": "access_token"},
        jti=str(new_jti)
    )

    # Step 6: Also rotate the refresh token with new JTI for better security
    new_refresh_token, new_refresh_exp = create_refresh_token(
        {"sub": str(user_id), "scope": "refresh_token"},
        jti=str(new_jti)
    )

    # Step 7: Update session record with all new tokens
    session.access_token = new_access_token
    session.access_token_expires_at = new_access_exp
    session.refresh_token = new_refresh_token
    session.refresh_token_expires_at = new_refresh_exp
    session.jti = new_jti
    session.last_active = datetime.utcnow()
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session





def is_valid_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    Returns: (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    email = email.strip().lower()
    
    # Basic email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check length
    if len(email) > 254:
        return False, "Email is too long (max 254 characters)"
    
    return True, None


def is_strong_password(password: str, min_length: int = 8) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?~`" for c in password)
    
    if not has_upper:
        return False, "Password must contain at least one uppercase letter"
    if not has_lower:
        return False, "Password must contain at least one lowercase letter"
    if not has_digit:
        return False, "Password must contain at least one digit"
    if not has_special:
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?~`)"
    
    return True, None


def is_valid_indian_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Indian phone number format.
    Accepts:
    - 10-digit numbers: 9XXXXXXXXX, 8XXXXXXXXX, 7XXXXXXXXX, 6XXXXXXXXX
    - With country code: +91-9XXXXXXXXX, +919XXXXXXXXX
    - With spaces/dashes: 91-9XXXXXXXXX, 91 9XXXXXXXXX
    Returns: (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number cannot be empty"
    
    phone = phone.strip()
    
    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-().]", "", phone)
    
    # Handle +91 country code
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91"):
        cleaned = cleaned[2:]
    
    # Validate: must be exactly 10 digits
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits (and optional formatting)"
    
    if len(cleaned) != 10:
        return False, "Phone number must be exactly 10 digits"
    
    # First digit must be 6, 7, 8, or 9 (Indian mobile standard)
    if cleaned[0] not in ["6", "7", "8", "9"]:
        return False, "Phone number must start with 6, 7, 8, or 9 (Indian format)"
    
    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format.
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must not exceed 50 characters"
    
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    
    return True, None


def is_valid_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Alias for is_valid_indian_phone for backward compatibility.
    """
    return is_valid_indian_phone(phone)

# ======================================================
# 2️⃣ Extract permissions for the current user

# 3️⃣ Invalidate permissions cache (called when permissions change)
# ======================================================
async def invalidate_permissions_cache(role_id: int):
    """
    Invalidate the permissions cache for a specific role.
    
    Called when permissions are assigned/revoked for a role to ensure all users
    with that role fetch fresh permissions on next request.
    
    Args:
        role_id (int): The role ID whose permissions were modified.
    
    Side Effects:
        - Deletes Redis cache key: `user_perms:{role_id}`.
        - Silently ignores Redis errors (cache invalidation failure non-blocking).
    """
    cache_key = f"user_perms:{role_id}"
    
    try:
        if redis:
            await redis.delete(cache_key)
            print(f"✅ Invalidated permission cache for role_id={role_id}")
    except Exception as e:
        # Cache invalidation failure should not block response
        print(f"⚠️  Redis cache invalidation failed for role_id={role_id}: {e}")
        pass

