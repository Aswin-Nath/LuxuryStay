# app/models/orm/status_utility.py
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base

class StatusUtility(Base):
    __tablename__ = "status_utility"

    status_id = Column(Integer, primary_key=True)
    category = Column(String(100), nullable=False)
    status_name = Column(String(50), nullable=False)
    status_code = Column(String(20), unique=True, nullable=False)
    is_active = Column(Boolean, server_default="true")
    description = Column(Text, nullable=True)

    # Defer relationship loading
    users = relationship("Users", back_populates="status", lazy="selectin")
