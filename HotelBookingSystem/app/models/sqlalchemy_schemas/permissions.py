from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.database.postgres_connection import Base


# =========================================================
# ENUM DEFINITIONS
# =========================================================
class Resources(str):
    """Resource constants matching database format"""
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


class PermissionTypes(str):
    """Permission type constants matching database format"""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    UPDATE = "UPDATE"


class Permissions(Base):
    __tablename__ = "permissions"

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    permission_name = Column(String(255), unique=True, index=True, nullable=False)
    # Format: "RESOURCE:PERMISSION" (e.g., "BOOKING:READ", "ADMIN_CREATION:WRITE")

    roles = relationship("PermissionRoleMap", back_populates="permission")


class PermissionRoleMap(Base):
    __tablename__ = "permission_role_map"

    role_id = Column(Integer, ForeignKey("roles_utility.role_id"), primary_key=True, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.permission_id"), primary_key=True, index=True)

    # Relationships
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles")
