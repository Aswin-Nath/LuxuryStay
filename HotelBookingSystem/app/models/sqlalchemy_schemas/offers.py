# ==============================================================
# app/models/postgres/offers.py
# Purpose: SQLAlchemy ORM for Offers Management
# ==============================================================

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, Boolean, ForeignKey, TIMESTAMP, CheckConstraint, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.postgres_connection import Base  # assuming declarative Base import


# ==============================================================
# OFFERS TABLE
# ==============================================================
class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(Integer, primary_key=True, autoincrement=True)
    offer_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    offer_price = Column(Numeric(10, 2), nullable=False, default=0)  # ✅ MUST EXIST
    offer_items = Column(JSON, nullable=True)  # Array of perks/features
    discount_percent = Column(Numeric(5, 2), CheckConstraint("discount_percent >= 0"), nullable=False)
    start_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    room_mappings = relationship(
        "OfferRoomMap",
        back_populates="offer",
        cascade="all, delete-orphan"
    )


# ==============================================================
# OFFER-ROOM MAP TABLE
# ==============================================================
class OfferRoomMap(Base):
    __tablename__ = "offer_room_map"

    offer_id = Column(Integer, ForeignKey("offers.offer_id", ondelete="CASCADE"), primary_key=True)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id"), primary_key=True)
    actual_price = Column(Numeric(12, 2), CheckConstraint("actual_price >= 0"), nullable=False)
    discounted_price = Column(Numeric(12, 2), CheckConstraint("discounted_price >= 0"), nullable=False)

    # Relationships
    offer = relationship("Offer", back_populates="room_mappings")
    room_type = relationship("RoomTypes", lazy="joined")
