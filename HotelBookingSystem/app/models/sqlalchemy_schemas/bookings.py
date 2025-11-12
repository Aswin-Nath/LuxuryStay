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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


class Bookings(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    # project uses `users` as customers table; using users.user_id as FK
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), index=True, nullable=False)
    room_count = Column(SmallInteger, nullable=False)
    check_in = Column(Date, nullable=False)
    check_in_time = Column(Time, server_default="12:00:00")
    check_out = Column(Date, nullable=False)
    check_out_time = Column(Time, server_default="11:00:00")
    total_price = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), nullable=False, server_default="Confirmed", index=True)
    is_deleted = Column(Boolean, server_default="false", index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    primary_customer_name = Column(Text, nullable=True)
    primary_customer_phone_number = Column(Text, nullable=True)
    primary_customer_dob = Column(Date, nullable=True)

    is_post_edit_done = Column(Boolean, server_default="false", nullable=True)
    is_pre_edit_done = Column(Boolean, server_default="false", nullable=True)
    
    # relationships
    rooms = relationship("BookingRoomMap", back_populates="booking", cascade="all, delete-orphan")
    taxes = relationship("BookingTaxMap", backref="booking", cascade="all, delete-orphan")


class BookingRoomMap(Base):
    __tablename__ = "booking_room_map"

    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.room_id"), primary_key=True, index=True)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id"), nullable=False)
    adults = Column(SmallInteger,server_default="1")
    children = Column(SmallInteger, server_default="0")
    is_pre_edited_room = Column(Boolean, server_default="false", nullable=True, index=True)
    is_post_edited_room = Column(Boolean, server_default="false", nullable=True, index=True)
    is_room_active = Column(Boolean, server_default="true", nullable=True, index=True)
    rating_given = Column(Integer, server_default="0", nullable=True)
    edit_suggested_rooms = Column(
        JSONB,
        nullable=True,
        comment="Array of room_ids suggested by admin for this booking room during post-edit",
    )
    booking = relationship("Bookings", back_populates="rooms")
    room = relationship("Rooms", back_populates="booking_room_maps")



class BookingTaxMap(Base):
    __tablename__ = "booking_tax_map"

    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), primary_key=True)
    tax_id = Column(Integer, ForeignKey("tax_utility.tax_id"), primary_key=True)
    tax_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class BookingEdits(Base):
    __tablename__ = "edit_bookings"

    edit_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    primary_customer_name = Column(String(150), nullable=False)
    primary_customer_phno = Column(String(20), nullable=False)
    primary_customer_dob = Column(Date, nullable=False)

    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    check_in_time = Column(TIMESTAMP(timezone=True), nullable=True)
    check_out_time = Column(TIMESTAMP(timezone=True), nullable=True)

    
    # Allow nullable total_price to match the API model which permits omission; callers may enforce non-null on DB level if needed
    total_price = Column(Numeric(12, 2), nullable=True)

    # optional status reference (project has a status_utility table)
    status_id = Column(Integer, ForeignKey("status_utility.status_id"), nullable=True)

    # edit type: PRE or POST
    edit_type = Column(String(10), nullable=False, index=True)
    edit_status = Column(String(50), server_default="PENDING", index=True)

    requested_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    requested_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # When admin suggests rooms, locks expire at this timestamp (UTC)
    lock_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    requested_room_changes = Column(
        JSONB,
        nullable=True,
        comment="Map of room_id -> requested new room_type_id by customer",
    )
    chosen_room_type = Column(
        Integer,
        ForeignKey("room_types.room_type_id", ondelete="SET NULL"),
        nullable=True,
        comment="Final chosen room type after edit approval",
    )
    is_deleted = Column(Boolean, server_default="false", index=True)
