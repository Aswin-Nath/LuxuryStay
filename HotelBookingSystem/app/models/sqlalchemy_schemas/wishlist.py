from sqlalchemy import Column, Integer, TIMESTAMP, Boolean, ForeignKey, func
from app.database.postgres_connection import Base


class Wishlist(Base):
    __tablename__ = "wishlist"

    wishlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.room_type_id"), index=True, nullable=True)
    offer_id = Column(Integer, ForeignKey("offers.offer_id"), index=True, nullable=True)
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    is_deleted = Column(Boolean, server_default="false", index=True)
