from sqlalchemy import Column,Integer,String,DateTime,func,Enum,ForeignKey,Date,Boolean,Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
from app.database.postgres_connection import Base
from app.models.orm.authorization import Roles
from app.models.orm.utility import StatusUtility
class GenderTypes(enum.Enum):
    Male="MALE"
    Female="FEMALE"
    Other="OTHER"

class Users(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles_utility.role_id"), nullable=False)
    full_name = Column(String(200), nullable=False)
    dob = Column(Date, nullable=True)
    gender = Column(Enum(GenderTypes, name="gender_types"), default=GenderTypes.Other)
    email = Column(String(150), unique=True, nullable=False)
    phone_number = Column(String(15), unique=True, nullable=True)
    hashed_password = Column(Text, nullable=False)
    last_password_updated = Column(DateTime, server_default=func.now())
    loyalty_points = Column(Integer, server_default="0")
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    status_id = Column(Integer, ForeignKey("status_utility.status_id"), nullable=True)
    is_deleted = Column(Boolean, server_default="false")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # relationships
    role = relationship("Roles", back_populates="users")
    status = relationship("StatusUtility", back_populates="users")
    creator = relationship("Users", remote_side=[user_id])
    sessions=relationship("Sessions",back_populates="user")
