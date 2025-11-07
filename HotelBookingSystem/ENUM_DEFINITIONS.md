# Enum Type Definitions - HotelBookingSystem

This document provides a comprehensive overview of all enums used throughout the HotelBookingSystem codebase.

## Overview

The HotelBookingSystem uses enums in two main contexts:
1. **SQLAlchemy Schema Enums** - For database-level constraints and validations
2. **Pydantic Model Enums** - For API request/response validation

---

## 1. Authentication Enums

### Located In: `app/models/sqlalchemy_schemas/authentication.py`

#### `VerificationType` (enum.Enum)
Used for email verification and password reset operations.

```python
class VerificationType(enum.Enum):
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"
    PHONE_OTP = "PHONE_OTP"
```

**Values:**
- `EMAIL_VERIFICATION` - Email verification for new accounts or email changes
- `PASSWORD_RESET` - Password reset verification
- `PHONE_OTP` - One-Time Password sent via phone

---

#### `TokenType` (enum.Enum)
Defines types of authentication tokens.

```python
class TokenType(enum.Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"
```

**Values:**
- `ACCESS` - Short-lived access token for API requests
- `REFRESH` - Long-lived refresh token for obtaining new access tokens

---

#### `RevokedType` (enum.Enum)
Specifies reasons for token revocation.

```python
class RevokedType(enum.Enum):
    AUTOMATIC_EXPIRED = "AUTOMATIC_EXPIRED"
    MANUAL_REVOKED = "MANUAL_REVOKED"
```

**Values:**
- `AUTOMATIC_EXPIRED` - Token was automatically revoked due to expiration
- `MANUAL_REVOKED` - Token was manually revoked by admin or user action

---

## 2. User Profile Enums

### Located In: `app/models/sqlalchemy_schemas/users.py` and `app/models/sqlalchemy_schemas/permissions.py`

#### `GenderTypes` (enum.Enum)
User gender classification for profile information.

**From `users.py`:**
```python
class GenderTypes(enum.Enum):
    Male = "MALE"
    Female = "FEMALE"
    Other = "OTHER"
```

**From `permissions.py`:**
```python
class GenderTypes(str, PyEnum):
    Male = "Male"
    Female = "Female"
    Other = "Other"
```

**Values:**
- `Male` / `MALE` - Male gender
- `Female` / `FEMALE` - Female gender
- `Other` / `OTHER` - Other gender or prefer not to say

> **Note:** There are two variants of this enum with different value formats. The SQLAlchemy schema uses uppercase (`MALE`, `FEMALE`, `OTHER`), while the permissions schema uses title case (`Male`, `Female`, `Other`).

---

## 3. Room Management Enums

### Located In: `app/models/sqlalchemy_schemas/rooms.py` and `app/schemas/pydantic_models/room.py`

#### `RoomStatus` (enum.Enum)
Tracks the operational status of a room.

**SQLAlchemy Schema:**
```python
class RoomStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"
    FROZEN = "FROZEN"
```

**Pydantic Model:**
```python
class RoomStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"
    FROZEN = "FROZEN"
```

**Values:**
- `AVAILABLE` - Room is available for booking
- `BOOKED` - Room is currently booked by a guest
- `MAINTENANCE` - Room is under maintenance and unavailable
- `FROZEN` - Room is temporarily frozen for a specific reason (see `FreezeReason`)

---

#### `FreezeReason` (enum.Enum)
Specifies the reason why a room is frozen.

**SQLAlchemy Schema:**
```python
class FreezeReason(enum.Enum):
    NONE = "NONE"
    CLEANING = "CLEANING"
    ADMIN_LOCK = "ADMIN_LOCK"
    SYSTEM_HOLD = "SYSTEM_HOLD"
```

**Pydantic Model:**
```python
class FreezeReason(str, Enum):
    NONE = "NONE"
    CLEANING = "CLEANING"
    ADMIN_LOCK = "ADMIN_LOCK"
    SYSTEM_HOLD = "SYSTEM_HOLD"
```

**Values:**
- `NONE` - Room is not frozen / default state
- `CLEANING` - Room is frozen for cleaning purposes
- `ADMIN_LOCK` - Room is locked by administrator action
- `SYSTEM_HOLD` - Room is held by the system for operational reasons

---

## 4. Issue Management Enums

### Located In: `app/models/sqlalchemy_schemas/issues.py` and `app/schemas/pydantic_models/issues.py`

#### `IssueStatus` (enum.Enum)
Tracks the lifecycle status of customer issues/complaints.

**SQLAlchemy Schema:**
```python
class IssueStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
```

**Pydantic Model:**
```python
class IssueStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
```

**Values:**
- `PENDING` - Issue has been reported but not yet reviewed
- `IN_PROGRESS` - Issue is being investigated/handled by support team
- `RESOLVED` - Issue has been resolved
- `CLOSED` - Issue is closed (may be resolved or dismissed)

---

## 5. Notification Enums

### Located In: `app/models/sqlalchemy_schemas/notifications.py`

#### `NotificationType` (PostgreSQL ENUM)
Classifies the type of notification being sent to users.

```python
notification_type_enum = ENUM(
    "SYSTEM",
    "PROMOTIONAL",
    "REMINDER",
    "TRANSACTIONAL",
    "SECURITY",
    "OTHER",
    name="notification_type",
    create_type=False,
)
```

**Values:**
- `SYSTEM` - System-level notifications (maintenance, updates, etc.)
- `PROMOTIONAL` - Marketing/promotional offers and deals
- `REMINDER` - Booking reminders, check-in reminders, etc.
- `TRANSACTIONAL` - Transaction confirmations, receipts, booking confirmations
- `SECURITY` - Security-related alerts (login attempts, password changes, etc.)
- `OTHER` - Other notification types (default)

---

#### `EntityType` (PostgreSQL ENUM)
Identifies the entity/resource that a notification relates to.

```python
entity_type_enum = ENUM(
    "BOOKING",
    "PAYMENT",
    "REFUND",
    "ISSUE",
    "OFFER",
    "REVIEW",
    "WISHLIST",
    "USER_ACCOUNT",
    "SYSTEM",
    "ROOM",
    name="entity_type_enum",
    create_type=False,
)
```

**Values:**
- `BOOKING` - Notification related to a booking
- `PAYMENT` - Notification related to payment processing
- `REFUND` - Notification related to refund requests
- `ISSUE` - Notification related to customer issues/complaints
- `OFFER` - Notification related to offers or promotions
- `REVIEW` - Notification related to reviews
- `WISHLIST` - Notification related to wishlist items
- `USER_ACCOUNT` - Notification related to user account/profile changes
- `SYSTEM` - System-level notifications
- `ROOM` - Notification related to room information/updates

---

## 6. Permission & Resource Enums

### Located In: `app/models/sqlalchemy_schemas/permissions.py`

#### `Resources` (str, PyEnum)
Defines all manageable resources in the system for role-based access control.

```python
class Resources(str, PyEnum):
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
```

**Values:**
- `BOOKING` - Booking-related operations
- `ADMIN_CREATION` - Admin user creation and management
- `ROOM_MANAGEMENT` - Room inventory and configuration management
- `PAYMENT_PROCESSING` - Payment handling and processing
- `REFUND_APPROVAL` - Refund request approval and processing
- `CONTENT_MANAGEMENT` - Content (images, descriptions, etc.) management
- `ISSUE_RESOLUTION` - Issue/complaint handling and resolution
- `NOTIFICATION_HANDLING` - Notification creation and management
- `ANALYTICS_VIEW` - View analytics and reports
- `BACKUP_OPERATIONS` - Backup creation and management
- `RESTORE_OPERATIONS` - Restore from backup operations
- `OFFER_MANAGEMENT` - Offer and promotion management

---

#### `PermissionTypes` (str, PyEnum)
Defines the types of permissions that can be granted on resources.

```python
class PermissionTypes(str, PyEnum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    MANAGE = "MANAGE"
    APPROVE = "APPROVE"
    EXECUTE = "EXECUTE"
```

**Values:**
- `READ` - Permission to view/read the resource
- `WRITE` - Permission to create or update the resource
- `DELETE` - Permission to delete the resource
- `MANAGE` - Full management permissions on the resource
- `APPROVE` - Permission to approve actions on the resource (e.g., refunds)
- `EXECUTE` - Permission to execute operations on the resource (e.g., backup)

---

## Enum Usage Pattern

### In SQLAlchemy Models
```python
from enum import Enum as PyEnum

class MyEnum(PyEnum):
    VALUE_1 = "VALUE_1"
    VALUE_2 = "VALUE_2"

class MyTable(Base):
    __tablename__ = "my_table"
    status = Column(Enum(MyEnum, name="my_enum"), nullable=False)
```

### In Pydantic Models (API Validation)
```python
from enum import Enum

class MyEnum(str, Enum):
    VALUE_1 = "VALUE_1"
    VALUE_2 = "VALUE_2"

class MyRequest(BaseModel):
    status: MyEnum
```

---

## Summary Table

| Enum Name | Location | Values Count | Primary Use |
|-----------|----------|--------------|------------|
| `VerificationType` | authentication.py | 3 | Email/Phone verification tracking |
| `TokenType` | authentication.py | 2 | JWT token classification |
| `RevokedType` | authentication.py | 2 | Token revocation reasons |
| `GenderTypes` | users.py, permissions.py | 3 | User profile gender field |
| `RoomStatus` | rooms.py | 4 | Room operational status |
| `FreezeReason` | rooms.py | 4 | Room freeze reason tracking |
| `IssueStatus` | issues.py | 4 | Issue lifecycle management |
| `NotificationType` | notifications.py | 6 | Notification categorization |
| `EntityType` | notifications.py | 10 | Notification entity linking |
| `Resources` | permissions.py | 12 | RBAC resource definition |
| `PermissionTypes` | permissions.py | 6 | RBAC permission types |

---

## Key Notes

1. **Dual Definition**: Some enums (e.g., `RoomStatus`, `IssueStatus`, `GenderTypes`) are defined in both SQLAlchemy schemas and Pydantic models. Keep them synchronized.

2. **PostgreSQL ENUM**: `NotificationType` and `EntityType` are defined using PostgreSQL's native ENUM type with `create_type=False` (already created in DB via migrations).

3. **String-based Enums**: Pydantic models use `str` mixins (`class X(str, Enum)`) for better JSON serialization and validation.

4. **Database Constraints**: SQLAlchemy enums enforce database-level constraints ensuring only valid values are stored.

5. **Migration Consideration**: Changes to enum values require database migrations to update existing PostgreSQL ENUM types.

---

## Migration Tracking

Database migrations defining these enums:
- File: `migrations/versions/c7f919222ca5_init_base_schema.py`
- Contains original ENUM definitions for all database-level enums

To add or modify enums:
1. Update the Python enum class
2. Create a new Alembic migration
3. Update the PostgreSQL ENUM type if necessary
4. Test thoroughly in development before production deployment
