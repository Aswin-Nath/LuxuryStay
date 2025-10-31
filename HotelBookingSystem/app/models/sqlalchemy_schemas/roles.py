from sqlalchemy import (
    Column,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base



# =========================================================
# ROLES TABLE
# =========================================================
class Roles(Base):
    __tablename__ = "roles_utility"

    role_id = Column(Integer, primary_key=True)
    role_name = Column(String, unique=True, nullable=False)
    role_description = Column(String, nullable=True)

    # Relationship: Role ↔ PermissionRoleMap
    permissions = relationship("PermissionRoleMap", back_populates="role")
    # Relationship: Role ↔ Users
    users = relationship("Users", back_populates="role")

