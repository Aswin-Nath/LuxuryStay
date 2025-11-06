from sqlalchemy import Column, Integer, Enum,UniqueConstraint,ForeignKey
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from enum import Enum as PyEnum

from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


# =========================================================
# ENUM DEFINITIONS
# =========================================================
# =========================================================
# ENUM DEFINITIONS
# =========================================================
class GenderTypes(str, PyEnum):
    Male = "Male"
    Female = "Female"
    Other = "Other"


class Resources(str, PyEnum):
    # canonical uppercase member names (match DB stored values)
    BOOKING = "BOOKING"
    ADMIN_CREATION = "ADMIN_CREATION"
    ROOM_MANAGEMENT = "ROOM_MANAGEMENT"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    REFUND_APPROVAL = "REFUND_APPROVAL"
    CONTENT_MANAGEMENT = "CONTENT_MANAGEMENT"
    ISSUE_RESOLUTION = "ISSUE_RESOLUTION"
    NOTIFICATION_HANDLING = "NOTIFICATION_HANDLING"
    ANALYTICS_VIEW = "ANALYTICS_VIEW"
    BACKUP_OPERATIONS = "BACKUP_OPERATIONS"
    RESTORE_OPERATIONS = "RESTORE_OPERATIONS"
    OFFER_MANAGEMENT = "OFFER_MANAGEMENT"

    # NOTE: previous mixed-case aliases removed — use uppercase underscore names (e.g. Resources.ROOM_MANAGEMENT)




class PermissionTypes(str, PyEnum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    MANAGE = "MANAGE"
    APPROVE = "APPROVE"
    EXECUTE = "EXECUTE"


class Permissions(Base):
    __tablename__ = "permissions"

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    resource = Column(Enum(Resources, name="resources", native_enum=False), unique=True, index=True, nullable=False)
    permission_type = Column(Enum(PermissionTypes, name="permission_types", native_enum=False), index=True, nullable=False)
    __table_args__ = (UniqueConstraint('resource', 'permission_type', name='unique_resource_permission'),)

    roles = relationship("PermissionRoleMap", back_populates="permission")

class PermissionRoleMap(Base):
    __tablename__ = "permission_role_map"

    role_id = Column(Integer, ForeignKey("roles_utility.role_id"), primary_key=True, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.permission_id"), primary_key=True, index=True)

    # Relationships
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles")
