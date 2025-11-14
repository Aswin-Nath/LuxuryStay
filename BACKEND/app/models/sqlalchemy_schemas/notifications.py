from sqlalchemy import (
	Column,
	Integer,
	Text,
	Boolean,
	TIMESTAMP,
	func,
	ForeignKey,
)
from sqlalchemy.dialects.postgresql import ENUM
from app.database.postgres_connection import Base


# ENUM definitions (must match PostgreSQL enums)
notification_type_enum = ENUM(
	"SYSTEM",
	"PROMOTIONAL",
	"REMINDER",
	"TRANSACTIONAL",
	"SECURITY",
	"OTHER",
	name="notification_type",
	create_type=False,  # already created in DB
)

entity_type_enum = ENUM(
	"BOOKING",
	"PAYMENT",
	"REFUND",
	"ISSUE",
	"REVIEW",
	"WISHLIST",
	"USER_ACCOUNT",
	"SYSTEM",
	"ROOM",
	name="entity_type_enum",
	create_type=False,  # already created in DB
)


class Notifications(Base):
	__tablename__ = "notifications"

	notification_id = Column(Integer, primary_key=True, autoincrement=True)
	recipient_user_id = Column(
		Integer,
		ForeignKey("users.user_id", ondelete="CASCADE"),
		index=True,
		nullable=False,
	)
	notification_type = Column(notification_type_enum, server_default="OTHER", nullable=False)
	entity_type = Column(entity_type_enum, nullable=True)
	entity_id = Column(Integer, nullable=True, index=True)
	title = Column(Text, nullable=False)
	message = Column(Text, nullable=False)
	is_read = Column(Boolean, server_default="false", nullable=False, index=True)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
	read_at = Column(TIMESTAMP(timezone=True), nullable=True)
	is_deleted = Column(Boolean, server_default="false", nullable=False, index=True)
