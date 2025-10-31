from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from app.database.postgres_connection import Base


class Images(Base):
	__tablename__ = "images"

	image_id = Column(Integer, primary_key=True, autoincrement=True)
	entity_type = Column(String(50), nullable=False)
	entity_id = Column(Integer, nullable=False)
	image_url = Column(Text, nullable=False)
	caption = Column(String(255), nullable=True)
	is_primary = Column(Boolean, server_default="false")
	uploaded_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
	is_deleted = Column(Boolean, server_default="false")

