# LuxuryStay Hotel Booking System - Copilot Instructions

## System Architecture Overview

**LuxuryStay** is a hybrid hotel booking platform with:
- **Backend**: FastAPI + PostgreSQL (relational) + MongoDB (logs/backups) + Redis (caching)
- **Frontend**: Angular 20+ with TailwindCSS
- **Key Pattern**: Service → CRUD → SQLAlchemy Models (async ORM)

### Data Flow
```
Client (Angular) → FastAPI Route → Service Layer → CRUD Layer → PostgreSQL/MongoDB → Redis Cache
```

## Backend Essentials

### Project Structure (`BACKEND/app/`)
- **routes/** - HTTP endpoints (18 modules: auth, rooms, bookings, payments, etc.)
- **services/** - Business logic; calls CRUD & validates rules
- **crud/** - Direct DB queries using SQLAlchemy async
- **models/sqlalchemy_schemas/** - PostgreSQL table definitions (Users, Bookings, Rooms, etc.)
- **core/** - security.py (JWT/auth), exceptions.py (custom HTTP exceptions), cache.py (Redis)
- **schemas/pydantic_models/** - Request/response validation schemas

### Critical Files
- **app/main.py** - App initialization, middleware setup, router registration
- **app/core/exceptions.py** - Custom exceptions (NotFoundException, ForbiddenException, etc.) returning structured JSON errors
- **app/dependencies/authentication.py** - `get_current_user` and `check_permission` functions
- **BACKEND/requirements.txt** - Python dependencies (FastAPI, SQLAlchemy, Motor, Redis, Loguru)

### Key Conventions

#### 1. **Async-First Pattern**
All DB operations must be async. Use `AsyncSession` from SQLAlchemy.
```python
# ✅ Correct
async def fetch_room(db: AsyncSession, room_id: int):
    res = await db.execute(select(Rooms).where(Rooms.room_id == room_id))
    return res.scalars().first()

# ❌ Wrong - blocking sync call
room = session.query(Rooms).get(room_id)
```

#### 2. **Exception Handling**
Always raise custom exceptions from `app.core.exceptions`. They return JSON with `error`, `status_code` fields.
```python
from app.core.exceptions import NotFoundException, ForbiddenException

if not room:
    raise NotFoundException("Room not found")
if not user.has_permission("ROOM_MANAGEMENT:READ"):
    raise ForbiddenException("You lack room access")
```

#### 3. **RBAC Permission Model**
Format: `"RESOURCE:PERMISSION"` (e.g., `"BOOKING:READ"`, `"ADMIN_CREATION:WRITE"`)
- Resources: BOOKING, ADMIN_CREATION, ROOM_MANAGEMENT, PAYMENT_PROCESSING, etc.
- Types: READ, WRITE, UPDATE, DELETE
- Check via: `check_permission(current_user, "RESOURCE:PERMISSION")`

#### 4. **Soft Deletes**
Most tables have `is_deleted` column (boolean, default=False). Always filter:
```python
stmt = select(Rooms).where(Rooms.is_deleted.is_(False))
```
Never use hard DELETE in CRUD unless specifically handling archive cleanup.

#### 5. **Service Layer Pattern**
Routes call services; services call CRUD. Services orchestrate business logic.
```python
# routes/rooms.py
@router.post("/create")
async def create_room(payload: RoomCreate, db: AsyncSession, user = Depends(get_current_user)):
    check_permission(user, "ROOM_MANAGEMENT:WRITE")
    return await svc_create_room(db, payload)  # Service handles validation + CRUD

# services/rooms.py
async def svc_create_room(db: AsyncSession, payload: RoomCreate):
    # Business logic validation
    existing = await crud.fetch_room_by_number(db, payload.room_no)
    if existing:
        raise ConflictException("Room number already exists")
    # CRUD call
    room = await crud.insert_room(db, payload.dict())
    await db.commit()
    return room
```

#### 6. **Caching Pattern** (Redis)
```python
from app.core.cache import get_cached, set_cached, invalidate_pattern

# Get with fallback
room = await get_cached(f"room:{room_id}", Room)
if not room:
    room = await crud.fetch_room_by_id(db, room_id)
    await set_cached(f"room:{room_id}", room, ttl=3600)

# Invalidate on update
await invalidate_pattern(f"room:{room_id}")
```

#### 7. **Pydantic Schemas**
Request/response validation in `app/schemas/pydantic_models/`. Use for type safety & API docs.
```python
# schemas/pydantic_models/room.py
class RoomCreate(BaseModel):
    room_no: str
    room_type_id: int
    amenity_ids: List[int] = []

class RoomResponse(BaseModel):
    room_id: int
    room_no: str
    room_type: RoomTypeResponse
    class Config:
        from_attributes = True
```

### Database Models Reference
Key tables (all in `app/models/sqlalchemy_schemas/`):
- **Users** - user_id (PK), email, role_id (FK), hashed_password, status, loyalty_points
- **Bookings** - booking_id, user_id (FK), check_in/check_out dates, total_price, status
- **BookingRoomMap** - links bookings to multiple rooms (many-to-many)
- **Rooms** - room_id, room_no, room_type_id (FK), status, hold_expires_at (for room locking)
- **RoomTypes** - room_type_id, type_name, price_per_night, max_adult/child counts
- **RoomAmenities** - amenity_id, amenity_name
- **Sessions** - JWT session tracking with access/refresh tokens
- **Permissions** - permission_name (format: "RESOURCE:PERMISSION")
- **PermissionRoleMap** - links roles to permissions

### Running Backend
```bash
cd BACKEND
python -m venv venv
venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# Access: http://localhost:8000/docs (Swagger) or /redoc
```

## Frontend Essentials

### Project Structure (`FRONTEND/hbs/src/`)
- **app/app.routes.ts** - Routing configuration
- **app/core/** - Services, interceptors, auth guards
- **app/features/** - Feature modules (rooms, bookings, payments, etc.)
- **app/services/** - API client services
- **assets/** - Static files

### Configuration
- **proxy.conf.json** - Dev proxy to backend (routes `/auth`, `/room-management`, `/profile` to `http://localhost:8000`)
- **package.json** - Scripts: `npm start` (ng serve), `npm run build`, `npm test`
- **tsconfig.json**, **angular.json** - TypeScript & Angular build config

### Running Frontend
```bash
cd FRONTEND/hbs
npm install
npm start
# Access: http://localhost:4200
```

## Key Feature: Room Hold/Lock System

**Problem**: Customers select rooms during checkout; system must hold them for 15 minutes or auto-release on payment failure.

**Solution**:
1. `POST /room-management/rooms/hold` - Locks rooms by setting `hold_expires_at` timestamp
2. `POST /room-management/rooms/unlock` - Releases rooms manually
3. Worker task - Runs every minute, auto-releases expired holds
4. Redis cache - Tracks session state with 15-min TTL

**Schema Support**: `Rooms.hold_expires_at` (DateTime) already exists.

## Common Development Tasks

### Adding a New Endpoint
1. Create route in `app/routes/{feature}.py`
2. Create service in `app/services/{feature}.py`
3. Create/update CRUD in `app/crud/{feature}.py`
4. Add Pydantic schema in `app/schemas/pydantic_models/{feature}.py`
5. Add SQLAlchemy model in `app/models/sqlalchemy_schemas/{feature}.py` (if new table)
6. Define permission format if new resource type needed in `app/models/sqlalchemy_schemas/permissions.py`

### Running Tests
```bash
# Backend
cd BACKEND
pytest tests/ -v

# Frontend
cd FRONTEND/hbs
npm test
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Important Patterns to Avoid

❌ **Blocking operations** - Never use sync DB calls; always await async operations  
❌ **Hard deletes** - Use soft deletes (is_deleted=True) unless explicitly confirmed  
❌ **Direct DB queries in routes** - Always go through services/CRUD  
❌ **Hardcoded strings for permissions** - Use resource constants from models  
❌ **Missing error handling** - Always catch exceptions and raise custom ones from `app.core.exceptions`
Never ever create documents as response
## External Dependencies
- **PostgreSQL 12+** - Primary relational database
- **MongoDB** - For logs, backups, config storage
- **Redis** - For caching and session management
- **Cloudinary** - Image upload/hosting integration
- **JWT (PyJWT)** - Token-based authentication
- **Loguru** - Structured logging

## Documentation References
- **Backend Design**: `BACKEND/docs/API_Documentation.md`, `BACKEND/docs/architecture.md`
- **Rooms Feature**: `START_HERE_ROOMS_ANALYSIS.md`, `ROOMS_MANAGEMENT_COMPREHENSIVE_ANALYSIS.md`
- **Room Hold System**: `ROOM_LOCK_RELEASE_INFRASTRUCTURE.md`
- **Booking Workflow**: `BOOKING_LIFECYCLE_QUICK_REFERENCE.md`
