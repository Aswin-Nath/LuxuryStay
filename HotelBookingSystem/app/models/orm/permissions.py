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
    Booking = "BOOKING"
    Admin_Creation = "ADMIN_CREATION"
    Room_Management = "ROOM_MANAGEMENT"
    Payment_Processing = "PAYMENT_PROCESSING"
    Refund_Approval = "REFUND_APPROVAL"
    Content_Management = "CONTENT_MANAGEMENT"
    Issue_Resolution = "ISSUE_RESOLUTION"
    Notification_Handling = "NOTIFICATION_HANDLING"
    Analytics_View = "ANALYTICS_VIEW"
    Backup_Operations = "BACKUP_OPERATIONS"
    Restore_Operations = "RESTORE_OPERATIONS"


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
    resource = Column(Enum(Resources, name="resources", native_enum=False), unique=True, nullable=False)
    permission_type = Column(Enum(PermissionTypes, name="permission_types", native_enum=False), nullable=False)
    __table_args__ = (UniqueConstraint('resource', 'permission_type', name='unique_resource_permission'),)

    roles = relationship("PermissionRoleMap", back_populates="permission")

class PermissionRoleMap(Base):
    __tablename__ = "permission_role_map"

    role_id = Column(Integer, ForeignKey("roles_utility.role_id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.permission_id"), primary_key=True)

    # Relationships
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles")
