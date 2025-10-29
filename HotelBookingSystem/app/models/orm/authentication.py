from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    SmallInteger,
    Text,
    ForeignKey,
    func,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database.postgres_connection import Base
import enum
import uuid


# ==========================================================
# ENUM DEFINITIONS (PostgreSQL ENUM equivalents)
# ==========================================================

class VerificationType(enum.Enum):
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"
    PHONE_OTP = "PHONE_OTP"


class TokenType(enum.Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


class RevokedType(enum.Enum):
    AUTOMATIC_EXPIRED = "AUTOMATIC_EXPIRED"
    MANUAL_REVOKED = "MANUAL_REVOKED"


# ==========================================================
# TABLE: verifications
# ==========================================================
class Verifications(Base):
    __tablename__ = "verifications"

    verification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    verification_type = Column(Enum(VerificationType, name="verification_type"), nullable=False)
    otp_code = Column(String(10), nullable=False)
    is_verified = Column(Boolean, server_default="false", nullable=False)
    attempt_count = Column(SmallInteger, server_default="0", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    verified_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # relationships
    user = relationship("Users", back_populates="verifications")


# ==========================================================
# TABLE: sessions
# ==========================================================
class Sessions(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False, unique=True)
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    login_time = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, server_default="true")
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(Text, nullable=True)

    # relationships
    user = relationship("Users", back_populates="sessions")
    blacklisted_tokens = relationship("BlacklistedTokens", back_populates="session")


# ==========================================================
# TABLE: blacklisted_tokens
# ==========================================================
class BlacklistedTokens(Base):
    __tablename__ = "blacklisted_tokens"

    token_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    token_type = Column(Enum(TokenType, name="token_type"), nullable=False)
    token_value_hash = Column(Text, unique=True, nullable=False)
    revoked_type = Column(Enum(RevokedType, name="revoked_type"), nullable=False)
    reason = Column(Text, nullable=True)
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)

    # relationships
    user = relationship("Users", back_populates="blacklisted_tokens")
    session = relationship("Sessions", back_populates="blacklisted_tokens")
