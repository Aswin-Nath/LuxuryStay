from sqlalchemy import Column,Integer,String,DateTime,func,ForeignKey,Text,Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from app.database.postgres_connection import Base

class GenderTypes(enum.Enum):
    Male="MALE"
    Female="FEMALE"
    Other="OTHER"

class Roles(Base):
    __tablename__="roles_utility"
    role_id=Column(Integer,primary_key=True)
    role_name=Column(String,unique=True,nullable=False)
    role_description=Column(String,nullable=True)
    created_at=Column(DateTime,server_default=func.now())

