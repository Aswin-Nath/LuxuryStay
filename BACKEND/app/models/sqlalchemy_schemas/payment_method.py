from sqlalchemy import Column, Integer, String
from app.database.postgres_connection import Base


class PaymentMethodUtility(Base):
    __tablename__ = "payment_method_utility"

    method_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
