from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    Text,
    Boolean,
    ForeignKey,
    TIMESTAMP,
    func,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


class Reviews(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="RESTRICT"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), index=True, nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id", ondelete="RESTRICT"), index=True, nullable=True)
    rating = Column(SmallInteger, nullable=False, index=True)
    comment = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=True)
    admin_response = Column(Text, nullable=True)
    responded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, server_default="false", index=True)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    # Relationships
    booking = relationship("Bookings", backref="reviews")
    user = relationship("Users", foreign_keys=[user_id])
    admin = relationship("Users", foreign_keys=[admin_id])
    room_type = relationship("RoomTypes")
