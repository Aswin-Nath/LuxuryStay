# ==============================================================
# app/models/orm/rooms.py
# Purpose: SQLAlchemy ORM models for Room Management module
# ==============================================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Enum as PgEnum,
    ForeignKey,
    Numeric,
    SmallInteger,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base
import enum

# ==============================================================
# ENUM DEFINITIONS
# ==============================================================
class RoomStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"
    FROZEN = "FROZEN"

class FreezeReason(enum.Enum):
    NONE = "NONE"
    CLEANING = "CLEANING"
    ADMIN_LOCK = "ADMIN_LOCK"
    SYSTEM_HOLD = "SYSTEM_HOLD"

# ==============================================================
# ROOM TYPES
# ==============================================================
class RoomTypes(Base):
    __tablename__ = "room_types"

    room_type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(50), nullable=False, unique=True, index=True)
    max_adult_count = Column(SmallInteger, nullable=False)
    max_child_count = Column(SmallInteger, nullable=False, default=0)
    price_per_night = Column(Numeric(12, 2), nullable=False, index=True)
    description = Column(Text, nullable=True)
    square_ft = Column(Integer, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rooms = relationship("Rooms", back_populates="room_type", cascade="all, delete-orphan")

# ==============================================================
# ROOMS
# ==============================================================
class Rooms(Base):
    __tablename__ = "rooms"

    room_id = Column(Integer, primary_key=True, autoincrement=True)
    room_no = Column(String(20), nullable=False, unique=True)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id", ondelete="RESTRICT"), index=True, nullable=False)
    room_status = Column(PgEnum(RoomStatus, name="room_status_enum"), nullable=False, default=RoomStatus.AVAILABLE, index=True)
    freeze_reason = Column(PgEnum(FreezeReason, name="freeze_reason_enum"), nullable=True)
    price_per_night = Column(Numeric(12, 2), nullable=False)
    max_adult_count = Column(SmallInteger, nullable=False)
    max_child_count = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    room_type = relationship("RoomTypes", back_populates="rooms")
    amenities = relationship("RoomAmenityMap", back_populates="room", cascade="all, delete-orphan")

# ==============================================================
# ROOM AMENITIES
# ==============================================================
class RoomAmenities(Base):
    __tablename__ = "room_amenities"

    amenity_id = Column(Integer, primary_key=True, autoincrement=True)
    amenity_name = Column(String(100), nullable=False, unique=True, index=True)

    # Relationships
    rooms = relationship("RoomAmenityMap", back_populates="amenity", cascade="all, delete-orphan")

# ==============================================================
# ROOM–AMENITY MAP (MANY-TO-MANY)
# ==============================================================
class RoomAmenityMap(Base):
    __tablename__ = "room_amenity_map"

    room_id = Column(Integer, ForeignKey("rooms.room_id", ondelete="CASCADE"), primary_key=True, index=True)
    amenity_id = Column(Integer, ForeignKey("room_amenities.amenity_id", ondelete="CASCADE"), primary_key=True, index=True)

    # Relationships
    room = relationship("Rooms", back_populates="amenities")
    amenity = relationship("RoomAmenities", back_populates="rooms")