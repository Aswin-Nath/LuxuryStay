# ==============================================================
# app/models/sqlalchemy_schemas/offers.py
# Purpose: SQLAlchemy ORM models for Offers/Discounts
# ==============================================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    Text,
    TIMESTAMP,
    Date,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


class Offers(Base):
    """
    Offers table: Stores offer/discount information.
    - offer_id: Unique identifier
    - offer_name: Name of the offer (e.g., "Summer Sale", "Early Bird")
    - description: Details about the offer
    - discount_percent: Discount percentage (e.g., 15 for 15%)
    - is_active: Whether offer is currently active
    - valid_from / valid_to: Offer validity period
    - max_uses: Maximum times offer can be used (NULL = unlimited)
    - room_types: JSONB storing room type configs with available count and discount %
      Format: [{"room_type_id": 1, "available_count": 5, "discount_percent": 15.50}, ...]
    - is_deleted: Soft delete flag
    """

    __tablename__ = "offers"

    offer_id = Column(Integer, primary_key=True, autoincrement=True)
    offer_name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    discount_percent = Column(Numeric(5, 2), nullable=False, comment="Base discount as percentage (e.g., 15.50)")
    room_types = Column(
        JSONB,
        nullable=False,
        default=[],
        comment="Array of {room_type_id, available_count, discount_percent} for this offer"
    )
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    valid_from = Column(Date, nullable=False, index=True)
    valid_to = Column(Date, nullable=False, index=True)
    max_uses = Column(Integer, nullable=True, comment="NULL = unlimited usage")
    current_uses = Column(Integer, nullable=False, default=0, comment="Current number of times used")
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
