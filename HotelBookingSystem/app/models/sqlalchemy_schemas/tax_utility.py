from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, TIMESTAMP, func
from app.database.postgres_connection import Base


class TaxUtility(Base):
    __tablename__ = "tax_utility"

    tax_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
