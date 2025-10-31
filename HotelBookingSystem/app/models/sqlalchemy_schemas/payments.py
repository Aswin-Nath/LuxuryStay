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


class Payments(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    method = Column(String(50), nullable=False)
    status = Column(String(50), server_default="PENDING")
    transaction_reference = Column(String(100), unique=True, nullable=True)
    remarks = Column(Text, nullable=True)
    is_deleted = Column(Boolean, server_default="false")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
