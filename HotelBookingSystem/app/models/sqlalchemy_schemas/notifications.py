from sqlalchemy import (
	Column,
	Integer,
	String,
	Text,
	Boolean,
	TIMESTAMP,
	func,
	ForeignKey,
)
from app.database.postgres_connection import Base


class Notifications(Base):
	__tablename__ = "notifications"

	notification_id = Column(Integer, primary_key=True, autoincrement=True)
	recipient_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
	notification_type = Column(String(50), server_default="OTHER")
	entity_type = Column(String(50), nullable=True)
	entity_id = Column(Integer, nullable=True)
	title = Column(String(150), nullable=False)
	message = Column(Text, nullable=False)
	is_read = Column(Boolean, server_default="false")
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
	is_deleted = Column(Boolean, server_default="false")
