from sqlalchemy import (
    Column,
    Integer,
    TIMESTAMP,
    Numeric,
    String,
    Text,
    Boolean,
    ForeignKey,
    func,
)
from app.database.postgres_connection import Base


class Refunds(Base):
    __tablename__ = "refunds"

    refund_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), server_default="INITIATED")
    refund_amount = Column(Numeric(12, 2), nullable=False)
    initiated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    remarks = Column(Text, nullable=True)
    is_deleted = Column(Boolean, server_default="false")
    transaction_method_id = Column(Integer, ForeignKey("payment_method_utility.method_id", ondelete="RESTRICT"), nullable=False)
    transaction_number = Column(String(100), nullable=True)



class RefundRoomMap(Base):
    __tablename__ = "refund_room_map"

    refund_id = Column(Integer, ForeignKey("refunds.refund_id", ondelete="CASCADE"), primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id"), primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.room_id"), primary_key=True)
    refund_amount = Column(Numeric(12, 2), nullable=False)
