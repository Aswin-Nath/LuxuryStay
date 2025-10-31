from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    Date,
    Time,
    TIMESTAMP,
    Numeric,
    Boolean,
    Text,
    String,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


class Bookings(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    # project uses `users` as customers table; using users.user_id as FK
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    room_count = Column(SmallInteger, nullable=False)
    check_in = Column(Date, nullable=False)
    check_in_time = Column(Time, server_default="12:00:00")
    check_out = Column(Date, nullable=False)
    check_out_time = Column(Time, server_default="11:00:00")
    total_price = Column(Numeric(12, 2), nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.offer_id"), nullable=True)
    offer_discount_percent = Column(Numeric(5, 2), server_default="0")
    status = Column(String(50), nullable=False, server_default="Confirmed")
    is_deleted = Column(Boolean, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    primary_customer_name = Column(Text, nullable=True)
    primary_customer_phone_number = Column(Text, nullable=True)
    primary_customer_dob = Column(Date, nullable=True)

    # relationships
    rooms = relationship("BookingRoomMap", back_populates="booking", cascade="all, delete-orphan")
    taxes = relationship("BookingTaxMap", backref="booking", cascade="all, delete-orphan")


class BookingRoomMap(Base):
    __tablename__ = "booking_room_map"

    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.room_id"), primary_key=True)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id"), nullable=False)
    adults = Column(SmallInteger, nullable=False)
    children = Column(SmallInteger, server_default="0")
    offer_discount_percent = Column(Numeric(5, 2), server_default="0")
    is_removed = Column(Boolean, server_default="false")
    removed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    modified_in_edit_id = Column(Integer, nullable=True)

    booking = relationship("Bookings", back_populates="rooms")


class BookingTaxMap(Base):
    __tablename__ = "booking_tax_map"

    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), primary_key=True)
    tax_id = Column(Integer, ForeignKey("tax_utility.tax_id"), primary_key=True)
    tax_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
