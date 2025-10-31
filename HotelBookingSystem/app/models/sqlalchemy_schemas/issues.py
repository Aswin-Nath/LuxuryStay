from sqlalchemy import (
	Column,
	Integer,
	String,
	Text,
	TIMESTAMP,
	Boolean,
	ForeignKey,
	func,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.database.postgres_connection import Base
import enum


class IssueStatus(enum.Enum):
	PENDING = "PENDING"
	IN_PROGRESS = "IN_PROGRESS"
	RESOLVED = "RESOLVED"
	CLOSED = "CLOSED"


class Issues(Base):
	__tablename__ = "issues"

	issue_id = Column(Integer, primary_key=True, autoincrement=True)
	booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="RESTRICT"), nullable=False)
	room_id = Column(Integer, ForeignKey("rooms.room_id"), nullable=True)
	user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
	title = Column(String(200), nullable=False)
	description = Column(Text, nullable=False)
	images = Column(JSONB, server_default="[]")
	status = Column(String(50), nullable=False, server_default=IssueStatus.PENDING.value)
	reported_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
	resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
	last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
	is_deleted = Column(Boolean, server_default="false")
	# resolved_by references the user (admin user) who resolved the issue.
	# Project does not have a separate `admins` table; reference `users.user_id`.
	resolved_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)


class IssueChat(Base):
	__tablename__ = "issue_chat"

	chat_id = Column(Integer, primary_key=True, autoincrement=True)
	issue_id = Column(Integer, ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False)
	sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
	message = Column(Text, nullable=False)
	sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
	is_deleted = Column(Boolean, server_default="false")

