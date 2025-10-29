from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


# ============================================
# PERMISSIONS TABLE
# ============================================
class Permissions(Base):
    __tablename__ = "permissions"

    permission_id = Column(Integer, primary_key=True)
    resource = Column(String(100), unique=True, nullable=False)
    permission_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # relationship to role-permission map
    roles = relationship("PermissionRoleMap", back_populates="permission")


# ============================================
# PERMISSION ↔ ROLE MAP (RBAC BRIDGE TABLE)
# ============================================
class PermissionRoleMap(Base):
    __tablename__ = "permission_role_map"

    role_id = Column(Integer, ForeignKey("roles_utility.role_id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.permission_id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


    # relationships
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles")