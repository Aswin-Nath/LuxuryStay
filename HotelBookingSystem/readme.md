# Hotel Booking System - Backend API

A FastAPI-based hotel booking platform with PostgreSQL and MongoDB, featuring room management, bookings, payments, reviews, and comprehensive admin tools.


---


## 🛠️ Tech Stack

### Core
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **Python 3.10+**

### Databases
- **PostgreSQL** - Relational data (SQLAlchemy ORM)
- **MongoDB** - Logs, backups, config (Motor driver)
- **Redis** - Caching (async)

### Authentication
- **PyJWT** - JWT tokens
- **Passlib + BCrypt** - Password hashing

### Additional
- **Pydantic** - Data validation
- **Loguru** - Logging
- **Aiofiles** - Async file operations
- **Pandas + Openpyxl** - Reports/Excel export

---
## 🔄 Request Flow

```
1. CLIENT REQUEST
   └─ POST /bookings + JWT Token

2. MIDDLEWARE PROCESSING
   ├─ CORS Check
   ├─ Error Handler
   └─ Logging

3. ROUTE HANDLER
   ├─ Validate JWT (get_current_user)
   ├─ Check permissions (RBAC)
   ├─ Validate request body (Pydantic)
   └─ Pass to Service

4. SERVICE LAYER
   ├─ Validate business logic
   ├─ Check Room availability (Room Service)
   ├─ Create booking via CRUD
   ├─ Update cache
   └─ Trigger notification (async)

5. DATA ACCESS LAYER
   ├─ Insert into PostgreSQL
   ├─ Log to MongoDB
   └─ Update Redis cache

6. BACKGROUND TASKS (Non-blocking)
   ├─ Send confirmation email
   ├─ Audit log
   └─ Update availability cache

7. RESPONSE
   └─ Return 201 + Booking details
```

---

## 📁 Project Structure

```
app/
├─ main.py ............................ App entry point, router registration
├─ core/
│  ├─ security.py ..................... JWT, password hashing
│  ├─ logger.py ....................... Logging setup
│  ├─ exceptions.py ................... Custom exceptions
│  ├─ cache.py ........................ Redis caching
│  └─ redis_manager.py ................ Redis connection
├─ routes/ (19 modules)
│  ├─ authentication/ ................. /auth endpoints
│  ├─ room_management/ ................ /rooms endpoints
│  ├─ booking_management/ ............. /bookings endpoints
│  ├─ payment_management/ ............. /payments endpoints
│  ├─ reviews_management/ ............. /reviews endpoints
│  ├─ wishlist_management/ ............ /wishlist endpoints
│  ├─ notifications_management/ ....... /notifications endpoints
│  ├─ issue_management/ ............... /issues endpoints
│  ├─ profile_management/ ............. /profile endpoints
│  ├─ logs_management/ ................ /logs endpoints
│  ├─ backup_and_restore_management/ .. /backups, /restores endpoints
│  ├─ report_management/ .............. /reports endpoints
│  ├─ roles_and_permissions_management /roles endpoints
│  ├─ content_management/ ............. /content endpoints
│  └─ ... (more feature modules)
├─ services/ (18 modules)
│  ├─ authentication_service/ ......... Login, signup, tokens
│  ├─ room_service/ ................... Room CRUD, availability
│  ├─ booking_service/ ................ Booking orchestration
│  ├─ payment_service/ ................ Payment processing
│  ├─ review_service/ ................. Reviews, ratings
│  ├─ notification_service/ ........... Email/SMS sending
│  ├─ wishlist_service/ ............... Wishlist operations
│  ├─ issue_service/ .................. Issue tracking
│  ├─ report_management/ .............. Analytics, reports
│  ├─ backup_restore_service/ ......... Backup/restore ops
│  ├─ images_service/ ................. Image upload/serving
│  ├─ audit_service/ .................. Audit logging
│  └─ ... (more services)
├─ crud/ (13 modules)
│  ├─ authentication/ ................. User, token queries
│  ├─ room_management/ ................ Room queries
│  ├─ booking_management/ ............. Booking queries
│  ├─ payment_management/ ............. Payment queries
│  └─ ... (more CRUD modules)
├─ schemas/
│  └─ pydantic_models/ ................ Request/response models
├─ models/
│  ├─ sqlalchemy_schemas/ ............. PostgreSQL tables
│  └─ motor_schemas/ .................. MongoDB schemas
├─ middlewares/
│  ├─ error_handler.py ................ Exception handling
│  └─ logging_middleware.py ........... Request logging
├─ dependencies/
│  └─ authentication.py ............... Auth dependencies
└─ database/
   ├─ postgres_connection.py .......... PostgreSQL setup
   ├─ mongo_connnection.py ............ MongoDB setup
   ├─ create_tables.py ................ Table initialization
   └─ seed_data.py .................... Initial data

tests/ ............................... Unit & integration tests
requirements.txt ..................... Python dependencies
```

---

## 🚀 Quick Start

### 1. Setup
```bash
# Clone & navigate
git clone <repo>
cd HotelBookingSystem

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Databases
Create `.env` file:
```env
# PostgreSQL
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_DB=hotel_booking_db

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=hotel_booking_mongo

# Redis (optional)
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
```

### 3. Initialize Databases
```bash
python database/create_tables.py      # PostgreSQL setup
python database/seed_data.py          # Initial data
```

### 4. Run Application
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI**: http://localhost:8000/openapi.json

---

## 📚 API Features

### Authentication (`/auth`)
- `POST /auth/signup` - Register new user
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Logout
- `POST /auth/request-otp` - Request OTP
- `POST /auth/verify-otp` - Verify OTP

### Rooms (`/rooms`)
- `GET /rooms` - List all rooms
- `GET /rooms/{id}` - Get room details
- `POST /rooms` - Create room (Admin)
- `PUT /rooms/{id}` - Update room (Admin)
- `DELETE /rooms/{id}` - Delete room (Admin)
- `POST /rooms/{id}/images` - Upload images (Admin)
- `GET /rooms/search` - Search rooms

### Bookings (`/bookings`)
- `GET /bookings` - User's bookings
- `POST /bookings` - Create booking
- `PUT /bookings/{id}` - Update booking
- `DELETE /bookings/{id}` - Cancel booking
- `POST /bookings/{id}/confirm` - Confirm booking
- `GET /bookings/admin/all` - All bookings (Admin)

### Payments (`/payments`)
- `POST /payments/process` - Process payment
- `GET /payments/{id}` - Payment details
- `POST /payments/{id}/refund` - Refund (Admin)
- `GET /payments/booking/{booking_id}` - Payment for booking

### Reviews (`/reviews`)
- `GET /reviews/room/{room_id}` - Room reviews
- `POST /reviews` - Create review
- `PUT /reviews/{id}` - Update review
- `DELETE /reviews/{id}` - Delete review


### Wishlist (`/wishlist`)
- `GET /wishlist` - Get wishlist
- `POST /wishlist/{room_id}` - Add to wishlist
- `DELETE /wishlist/{room_id}` - Remove from wishlist

### Issues (`/issues`)
- `GET /issues` - List issues
- `POST /issues` - Create issue
- `PUT /issues/{id}` - Update issue
- `POST /issues/{id}/resolve` - Resolve issue (Admin)

### Notifications (`/notifications`)
- `GET /notifications` - Get notifications
- `PUT /notifications/{id}/read` - Mark as read
- `DELETE /notifications/{id}` - Delete notification

### Reports (`/reports`) - Admin only
- `GET /reports/bookings` - Booking analytics
- `GET /reports/revenue` - Revenue report
- `GET /reports/occupancy` - Room occupancy
- `POST /reports/export` - Export to Excel

### Backup/Restore (`/backups`, `/restores`) - Admin only
- `POST /backups/create` - Create backup
- `GET /backups` - List backups
- `POST /restores/create` - Restore from backup

### Audit Logs (`/logs`)
- `GET /logs/audit` - Audit logs
- `GET /logs/booking` - Booking logs
- `GET /logs/audit/user/{user_id}` - User activity

### Roles & Permissions (`/roles`) - Admin only
- `GET /roles` - List roles
- `POST /roles` - Create role
- `POST /roles/{id}/permissions` - Assign permissions

---

## 🔐 Authentication & Security

### JWT Flow
```
1. User Login
   └─ Credentials validated
      └─ JWT Access token (15 min) + Refresh token (7 days)

2. API Request
   └─ Authorization: Bearer <token>
      └─ Token decoded and validated
         └─ Request processed

3. Token Expired
   └─ Refresh endpoint called
      └─ New Access token issued
         └─ Old token revoked
```

### Password Security
- ✅ Bcrypt hashing with salt
- ✅ Minimum 8 characters
- ✅ Password change available
- ✅ Reset via OTP

### RBAC (Role-Based Access Control)
- **Roles**: customer, manager, admin, staff
- **Permissions**: CREATE, READ, UPDATE, DELETE per resource
- **Resources**: ROOMS, BOOKINGS, PAYMENTS, USERS, REPORTS, etc.

---

## 🗄️ Database Schema

### PostgreSQL Tables

**Users**
- id, email (UNIQUE), password_hash, full_name, phone, gender, profile_image, role_id, created_at, updated_at

**Rooms**
- id, name, description, price_per_night, capacity, room_type, status, floor_number, created_at, updated_at

**Bookings**
- id, user_id (FK), room_id (FK), check_in_date, check_out_date, guests, total_price, status, special_requests, created_at, updated_at

**Payments**
- id, booking_id (FK), amount, payment_method, transaction_id, status, created_at, updated_at

**Reviews**
- id, booking_id (FK), user_id (FK), room_id (FK), rating (1-5), title, comment, cleanliness_rating, comfort_rating, service_rating, created_at, updated_at

**Wishlist**
- id, user_id (FK), room_id (FK), created_at



**Issues**
- id, user_id (FK), booking_id (FK), title, description, status, priority, assigned_to (FK), created_at, updated_at

**Roles & Permissions**
- role: id, name (UNIQUE), description
- permission: id, resource, action, description

### MongoDB Collections

**audit_logs**
- _id, user_id, action, resource_type, resource_id, changes (Object), timestamp, ip_address

**booking_logs**
- _id, booking_id, event_type, event_data (Object), created_by, timestamp

**notifications**
- _id, user_id, type, title, message, is_read, related_booking_id, created_at

**backups**
- _id, backup_name, backup_type (FULL/INCREMENTAL), file_path, size_mb, created_by, created_at, expires_at, metadata

**system_config**
- _id, config_key, config_value, updated_at

---

## 🎯 Key Design Patterns

### 1. **Layered Architecture**
   - Routes → Services → CRUD → Database
   - Clear separation of concerns
   - Easy to test and maintain

### 2. **Dependency Injection**
   - FastAPI `Depends()` for auth, db, cache
   - Loose coupling
   - Easy mocking for tests

### 3. **Repository Pattern**
   - CRUD modules abstract data access
   - Easy database switching

### 4. **Service Orchestration**
   - Services call other services
   - Business logic centralized
   - Reusable components

### 5. **Async/Await**
   - All I/O operations async
   - Non-blocking notifications
   - Better performance

---

## 💡 Development Tips

### Adding a New Feature
1. **Create Route** in `app/routes/feature_name/`
2. **Create Service** in `app/services/feature_name_service/`
3. **Create CRUD** in `app/crud/feature_name/` if needed
4. **Create Models** in `app/schemas/pydantic_models/`
5. **Register Route** in `app/main.py`
6. **Add Tests** in `tests/`

### Best Practices
- ✅ Validate input at route level
- ✅ Apply business logic in services
- ✅ Use CRUD for database operations
- ✅ Handle errors with custom exceptions
- ✅ Log important actions
- ✅ Use cache for frequent queries
- ✅ Make notifications async
- ✅ Document API endpoints

### Forbidden Patterns
- ❌ Direct database queries in routes
- ❌ Circular service dependencies
- ❌ Blocking operations in endpoints
- ❌ Unvalidated input
- ❌ Hardcoded secrets

---

### Manual Deployment
```bash
# Production run (no reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---
