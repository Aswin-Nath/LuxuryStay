# 🏨 ROOMS MANAGEMENT MODULE - COMPREHENSIVE ANALYSIS & STRATEGY

**Date:** November 28, 2025  
**Target:** Complete Room Management for Booking Module Integration  
**Timeline:** Tomorrow (Day 2)  
**Session Duration:** 15 mins per booking session (booking + payment + lock/release)

---

## 📊 TABLE OF CONTENTS

1. [Current State Analysis](#current-state-analysis)
2. [Database Architecture](#database-architecture)
3. [15-Minute Session Strategy](#15-minute-session-strategy)
4. [Room Locking Mechanism](#room-locking-mechanism)
5. [Room Availability Calculation](#room-availability-calculation)
6. [Frontend Architecture](#frontend-architecture)
7. [Implementation Roadmap](#implementation-roadmap)
8. [API Endpoints Reference](#api-endpoints-reference)

---

## 📋 CURRENT STATE ANALYSIS

### ✅ BACKEND - WHAT EXISTS

#### Database Schema (Rooms Module)
```
┌─────────────────────┐
│   RoomTypes         │
├─────────────────────┤
│ PK: room_type_id    │
│ type_name           │
│ max_adult_count     │
│ max_child_count     │
│ price_per_night     │ ← BASE PRICE (used for all rooms of this type)
│ description         │
│ square_ft           │
│ is_deleted          │
│ created_at          │
│ updated_at          │
└─────────────────────┘
         │
         │ (1:M)
         ▼
┌─────────────────────┐
│   Rooms             │
├─────────────────────┤
│ PK: room_id         │
│ room_no             │ ← UNIQUE IDENTIFIER (e.g., "101", "202")
│ FK: room_type_id    │ ← links to room type
│ room_status         │ ← CRITICAL: AVAILABLE|BOOKED|MAINTENANCE|FROZEN|HELD
│ freeze_reason       │ ← WHY FROZEN: CLEANING|ADMIN_LOCK|SYSTEM_HOLD
│ hold_expires_at     │ ← ⭐ TIMESTAMP FOR SESSION TIMEOUT
│ created_at          │
│ updated_at          │
│ is_deleted          │
└─────────────────────┘
         │
         ├─(M:M)─► RoomAmenityMap ─► RoomAmenities
         │
         └─(1:M)─► BookingRoomMap ◄────────────────┐
                                                    │
                                    ┌──────────────┴─────────────┐
                                    ▼                            ▼
                            ┌──────────────┐        ┌─────────────────┐
                            │  Bookings    │        │ BookingRoomMap  │
                            ├──────────────┤        ├─────────────────┤
                            │ booking_id   │        │ booking_id (FK) │
                            │ user_id (FK) │        │ room_id (FK)    │
                            │ check_in     │        │ room_type_id    │
                            │ check_out    │        │ adults          │
                            │ total_price  │        │ children        │
                            │ status       │        │ is_room_active  │
                            │ created_at   │        └─────────────────┘
                            └──────────────┘
```

#### Room Status States
```
┌─────────────────────────────────────────────────────┐
│         ROOM STATUS LIFECYCLE                        │
└─────────────────────────────────────────────────────┘

AVAILABLE (Default)
    ↓
    ├─→ HELD (when user selects during booking) ← ⭐ 15-MIN TIMER STARTS
    │     ├─→ AVAILABLE (if payment fails or session expires)
    │     └─→ BOOKED (if payment succeeds)
    │
    ├─→ MAINTENANCE (admin freezes for cleaning)
    │     └─→ AVAILABLE (admin unfreezes)
    │
    └─→ FROZEN (with freeze_reason = ADMIN_LOCK/SYSTEM_HOLD)
         └─→ AVAILABLE (admin unfreezes)
```

#### Current Backend APIs (Rooms Routes)
```python
✅ POST   /room-management/types              → Create room type
✅ GET    /room-management/types              → List room types (cached 300s)
✅ PUT    /room-management/types/{id}         → Update room type
✅ DELETE /room-management/types/{id}         → Soft delete room type

✅ POST   /room-management/rooms              → Create room
✅ GET    /room-management/rooms              → List rooms (filters: room_type_id, status_filter, is_freezed)
✅ GET    /room-management/rooms/{id}         → Get single room
✅ PUT    /room-management/rooms/{id}         → Update room
✅ DELETE /room-management/rooms/{id}         → Soft delete room

✅ POST   /room-management/rooms/bulk-upload  → Bulk upload from Excel
✅ POST   /room-management/types/{id}/images  → Upload room type images
✅ GET    /room-management/types/{id}/images  → Get room type images

✅ POST   /room-management/amenities          → Create amenity
✅ GET    /room-management/amenities          → List amenities
✅ POST   /room-management/amenities/map      → Map amenity to room
✅ DELETE /room-management/amenities/unmap    → Unmap amenity from room
```

### ⚠️ BACKEND - WHAT'S MISSING

```
❌ NO ROOM LOCKING API (to set HELD status with 15-min expiry)
❌ NO ROOM UNLOCK API (to revert from HELD to AVAILABLE)
❌ NO AVAILABILITY CHECK BY DATE RANGE (for booking calendar)
❌ NO BULK ROOM HOLD (to hold multiple rooms for multi-room bookings)
❌ NO SCHEDULED WORKER to expire holds after 15 minutes
```

### ⚠️ FRONTEND - WHAT EXISTS

```
✅ RoomsService in core/services/rooms/
   ├─ getRoomTypes()
   └─ getRooms(roomTypeId?, isFreezed?, statusFilter?)

✅ Permission guards for ROOM_MANAGEMENT scope
✅ Basic auth interceptor
```

### ❌ FRONTEND - WHAT'S MISSING

```
❌ Admin Room Management Module
   ├─ Room list view
   ├─ Room create/edit component
   ├─ Room status management UI
   └─ Amenity management UI

❌ Customer Room Browsing Module
   ├─ Room search/filter
   ├─ Room availability calendar
   └─ Room selection with hold system

❌ Room Hold/Lock UI Components
   ├─ Visual 15-min timer countdown
   └─ Session timeout warning

❌ Room availability calculation logic
```

---

## 🗄️ DATABASE ARCHITECTURE

### Room Status Field (Enum)
```sql
CREATE TYPE room_status_enum AS ENUM (
  'AVAILABLE',      -- Ready for booking
  'BOOKED',         -- Currently has active booking
  'MAINTENANCE',    -- Under maintenance (freeze_reason = CLEANING)
  'FROZEN',         -- Locked by admin or system
  'HELD'            -- Temporarily held during booking (new status needed)
);

CREATE TYPE freeze_reason_enum AS ENUM (
  'NONE',           -- No freeze
  'CLEANING',       -- Being cleaned
  'ADMIN_LOCK',     -- Manually locked by admin
  'SYSTEM_HOLD'     -- System hold during booking session
);
```

### Critical Fields for Session Management
```sql
-- In Rooms table:
hold_expires_at TIMESTAMP WITH TIME ZONE  -- When the 15-min hold expires
room_status ROOM_STATUS_ENUM              -- Current status (HELD when in booking)
freeze_reason FREEZE_REASON_ENUM          -- Why it's in that status

-- Example:
┌────────┬───────────┬──────────────────────┬──────────────┐
│room_id │room_status│hold_expires_at       │freeze_reason │
├────────┼───────────┼──────────────────────┼──────────────┤
│  101   │  HELD     │2025-11-28 14:30:45   │SYSTEM_HOLD   │
│  102   │  HELD     │2025-11-28 14:31:20   │SYSTEM_HOLD   │
│  103   │AVAILABLE  │NULL                  │NONE          │
└────────┴───────────┴──────────────────────┴──────────────┘
```

---

## ⏱️ 15-MINUTE SESSION STRATEGY

### Session Flow (Booking + Payment + Lock/Release)

```
┌─────────────────────────────────────────────────────────────────┐
│           CUSTOMER BOOKING FLOW (15-MINUTE WINDOW)              │
└─────────────────────────────────────────────────────────────────┘

T=0:00  START
    │
    ├─→ [CUSTOMER BROWSING]
    │   ├─ View available rooms (GET /room-management/rooms)
    │   └─ Check room details, amenities, images
    │
    ├─→ [CUSTOMER SELECTS ROOMS]
    │   ├─ POST /room-management/rooms/{id}/hold
    │   ├─ Response: {"room_id": 101, "held_until": "2025-11-28T14:30:45Z"}
    │   ├─ Frontend: Show countdown timer (15:00)
    │   └─ Room status changes: AVAILABLE → HELD
    │       (Database: hold_expires_at = NOW() + 15 minutes)
    │
T=0:15  [PAYMENT PROCESSING] ←──── CRITICAL WINDOW
    │   ├─ Customer enters payment details
    │   ├─ POST /payments/process-payment
    │   │   └─ If SUCCESSFUL:
    │   │      ├─ POST /bookings/create
    │   │      │  └─ Creates booking + BookingRoomMap
    │   │      ├─ Room status: HELD → BOOKED
    │   │      └─ hold_expires_at = NULL
    │   │
    │   │   └─ If FAILED:
    │   │      ├─ POST /room-management/rooms/{id}/unlock
    │   │      ├─ Room status: HELD → AVAILABLE
    │   │      └─ hold_expires_at = NULL
    │   │
    ├─→ [CLEANUP]
    │   ├─ If session reaches 15:00 without payment:
    │   │  └─ Worker task expires hold automatically
    │   │     └─ Room status: HELD → AVAILABLE
    │   │
    └─→ END

Key Points:
✅ Only 15 minutes to complete payment
✅ If payment fails → release hold immediately
✅ If session expires → worker releases hold
✅ If payment succeeds → lock room permanently (until checkout)
```

### Session State in Redis (for quick lookups)

```json
{
  "booking_session:{session_id}": {
    "user_id": 1,
    "room_ids": [101, 102],
    "held_at": "2025-11-28T14:15:45Z",
    "expires_at": "2025-11-28T14:30:45Z",
    "check_in": "2025-12-01",
    "check_out": "2025-12-03",
    "rooms": [
      {
        "room_id": 101,
        "room_no": "101",
        "room_type_id": 1,
        "price_per_night": 150.00,
        "nights": 2,
        "room_total": 300.00
      }
    ],
    "total_price": 300.00,
    "payment_status": "pending"
  }
}
```

---

## 🔐 ROOM LOCKING MECHANISM

### 🟢 Backend APIs Needed (TO IMPLEMENT TOMORROW)

```python
# ============================================
# 1. LOCK ROOM(S) FOR BOOKING SESSION
# ============================================
POST /room-management/rooms/hold
Body: {
  "room_ids": [101, 102],          # Multiple rooms for multi-room bookings
  "check_in": "2025-12-01",        # For validation
  "check_out": "2025-12-03"
}
Response: {
  "successfully_held": [
    {
      "room_id": 101,
      "held_until": "2025-11-28T14:30:45Z",
      "room_no": "101",
      "room_type_id": 1
    }
  ],
  "failed": [
    {
      "room_id": 103,
      "reason": "Room already booked for these dates"
    }
  ]
}
Status: 200 OK

# Implementation:
# 1. Check if rooms are AVAILABLE for date range
# 2. Set status = HELD
# 3. Set freeze_reason = SYSTEM_HOLD
# 4. Set hold_expires_at = NOW() + 15 minutes
# 5. Cache booking session in Redis
# 6. Return response with all details


# ============================================
# 2. UNLOCK ROOM(S) AFTER SESSION EXPIRES
# ============================================
POST /room-management/rooms/unlock
Body: {
  "room_ids": [101, 102],
  "reason": "payment_failed" | "session_expired"
}
Response: {
  "successfully_released": [101, 102],
  "failed": []
}
Status: 200 OK

# Implementation:
# 1. Check rooms have status = HELD
# 2. Set status = AVAILABLE
# 3. Set freeze_reason = NONE
# 4. Set hold_expires_at = NULL
# 5. Clear from Redis cache
# 6. Return response


# ============================================
# 3. CHECK ROOM AVAILABILITY BY DATE RANGE
# ============================================
GET /room-management/rooms/availability
Query: {
  "check_in": "2025-12-01",
  "check_out": "2025-12-03",
  "room_type_id": 1 (optional),
  "adult_count": 2,
  "child_count": 0
}
Response: {
  "available_rooms": [
    {
      "room_id": 101,
      "room_no": "101",
      "room_type_id": 1,
      "room_type": {
        "type_name": "Deluxe",
        "price_per_night": 150.00,
        "square_ft": 500,
        "amenities": ["WiFi", "AC", "TV"]
      },
      "amenities": ["WiFi", "AC", "TV"],
      "images": [{url, is_primary}],
      "nights": 2,
      "total_price": 300.00
    }
  ],
  "unavailable_count": 3,
  "total_available": 5
}

# Implementation:
# 1. Query bookings for date range (overlapping dates)
# 2. Query rooms with status NOT IN (BOOKED, MAINTENANCE, FROZEN)
# 3. Exclude HELD rooms (unless expired)
# 4. Filter by room_type_id and occupancy if provided
# 5. Calculate price for date range
# 6. Include amenities and images
# 7. Return paginated response


# ============================================
# 4. SCHEDULED WORKER - EXPIRE HOLDS
# ============================================
# Runs every 1 minute
Worker: /app/workers/release_room_holds_worker.py

Logic:
  1. Find all rooms where:
     - status = HELD
     - hold_expires_at <= NOW()
  2. For each room:
     - Set status = AVAILABLE
     - Set freeze_reason = NONE
     - Set hold_expires_at = NULL
     - Log action
  3. Notify customer (optional): "Your session expired"
  4. Clear Redis cache
```

### 🟠 Database Migrations Needed

```sql
-- Add hold_expires_at column (if not present)
ALTER TABLE rooms ADD COLUMN hold_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add index for performance
CREATE INDEX idx_rooms_hold_expires_at 
ON rooms(hold_expires_at) 
WHERE room_status = 'HELD';

-- Add unique constraint for room_no (if not present)
ALTER TABLE rooms ADD CONSTRAINT uq_room_no UNIQUE (room_no);
```

---

## 📅 ROOM AVAILABILITY CALCULATION

### Availability Query Logic

```sql
-- GET /room-management/rooms/availability
-- Find rooms available for check_in to check_out

SELECT DISTINCT r.*
FROM rooms r
JOIN room_types rt ON r.room_type_id = rt.room_type_id
LEFT JOIN bookings b ON 1=1
LEFT JOIN booking_room_map brm ON brm.room_id = r.room_id AND b.booking_id = brm.booking_id
WHERE
  -- Not deleted
  r.is_deleted = FALSE
  AND rt.is_deleted = FALSE
  
  -- Not in permanent lock states
  AND r.room_status NOT IN ('BOOKED', 'MAINTENANCE')
  AND NOT (r.room_status = 'FROZEN' AND r.freeze_reason IN ('ADMIN_LOCK', 'CLEANING'))
  
  -- Either AVAILABLE or HELD with expired hold
  AND (
    r.room_status = 'AVAILABLE'
    OR (r.room_status = 'HELD' AND r.hold_expires_at < NOW())
  )
  
  -- No booking overlap
  AND NOT EXISTS (
    SELECT 1 FROM bookings b2
    JOIN booking_room_map brm2 ON b2.booking_id = brm2.booking_id
    WHERE brm2.room_id = r.room_id
    AND b2.status != 'Cancelled'
    AND (
      (b2.check_in < :check_out AND b2.check_out > :check_in)
    )
  )
  
  -- Match occupancy requirements
  AND rt.max_adult_count >= :adult_count
  AND rt.max_child_count >= :child_count
  
  -- Optional: filter by room type
  AND (:room_type_id IS NULL OR r.room_type_id = :room_type_id)

ORDER BY r.room_no;
```

### Availability Calculation in Frontend

```typescript
// Angular: Calculate availability for display

interface RoomAvailability {
  room_id: number;
  room_no: string;
  available: boolean;
  reason?: string; // "booked", "maintenance", "held"
  held_until?: Date;
}

calculateRoomAvailability(
  rooms: Room[],
  checkIn: Date,
  checkOut: Date,
  bookings: Booking[]
): RoomAvailability[] {
  const now = new Date();
  
  return rooms.map(room => {
    // Check if currently held and hold expired
    if (room.room_status === 'HELD' && room.hold_expires_at) {
      if (new Date(room.hold_expires_at) < now) {
        return { room_id: room.room_id, room_no: room.room_no, available: true };
      }
      return {
        room_id: room.room_id,
        room_no: room.room_no,
        available: false,
        reason: 'held',
        held_until: new Date(room.hold_expires_at)
      };
    }
    
    // Check permanent locks
    if (room.room_status === 'FROZEN' || room.room_status === 'MAINTENANCE') {
      return {
        room_id: room.room_id,
        room_no: room.room_no,
        available: false,
        reason: room.room_status.toLowerCase()
      };
    }
    
    // Check booking conflicts
    const hasConflict = bookings.some(booking =>
      booking.rooms.some(br =>
        br.room_id === room.room_id &&
        new Date(booking.check_in) < checkOut &&
        new Date(booking.check_out) > checkIn &&
        booking.status !== 'Cancelled'
      )
    );
    
    return {
      room_id: room.room_id,
      room_no: room.room_no,
      available: !hasConflict,
      reason: hasConflict ? 'booked' : undefined
    };
  });
}
```

---

## 🎨 FRONTEND ARCHITECTURE

### Component Structure

```
src/app/features/rooms-management/
├── admin/
│   ├── room-list/
│   │   ├── room-list.component.ts
│   │   ├── room-list.component.html
│   │   └── room-list.component.css
│   ├── room-create-edit/
│   │   ├── room-create-edit.component.ts
│   │   ├── room-create-edit.component.html
│   │   └── room-create-edit.component.css
│   ├── room-type-management/
│   │   ├── room-type-list.component.ts
│   │   └── ...
│   ├── amenity-management/
│   │   ├── amenity-list.component.ts
│   │   └── ...
│   └── room-availability-status/
│       ├── room-availability-status.component.ts
│       └── ...
│
├── customer/
│   ├── room-search/
│   │   ├── room-search.component.ts
│   │   ├── room-search.component.html
│   │   └── room-search.component.css
│   ├── room-details/
│   │   ├── room-details.component.ts
│   │   └── ...
│   ├── room-selection/
│   │   ├── room-selection.component.ts
│   │   ├── room-card.component.ts
│   │   └── room-selector-modal.component.ts
│   └── availability-calendar/
│       ├── availability-calendar.component.ts
│       └── ...
│
├── shared/
│   ├── room-status-badge/
│   ├── availability-timer/
│   │   ├── availability-timer.component.ts (15-min countdown)
│   │   └── availability-timer.component.html
│   └── room-amenities-display/
│
├── models/
│   ├── room.model.ts
│   ├── room-type.model.ts
│   ├── room-availability.model.ts
│   └── booking-session.model.ts
│
├── services/
│   ├── room-management.service.ts (admin operations)
│   ├── room-availability.service.ts (search & filter)
│   ├── room-hold.service.ts (booking session locking)
│   ├── room-type-management.service.ts
│   └── amenity-management.service.ts
│
└── rooms.module.ts
```

### Service Layer Architecture

```typescript
// 1. RoomManagementService (Admin Operations)
@Injectable({ providedIn: 'root' })
export class RoomManagementService {
  // CRUD operations for rooms
  createRoom(payload: RoomCreate): Observable<RoomResponse>
  updateRoom(roomId: number, payload: RoomUpdate): Observable<RoomResponse>
  deleteRoom(roomId: number): Observable<any>
  listRooms(filters?: RoomFilters): Observable<Room[]>
  getRoomById(roomId: number): Observable<RoomResponse>
}

// 2. RoomAvailabilityService (Customer Search)
@Injectable({ providedIn: 'root' })
export class RoomAvailabilityService {
  // Search and filter available rooms
  getAvailableRooms(checkIn: Date, checkOut: Date, filters?: AvailabilityFilters): Observable<RoomAvailability[]>
  searchRoomsByType(roomType: number, checkIn: Date, checkOut: Date): Observable<Room[]>
  getAvailabilityCalendar(roomTypeId: number): Observable<CalendarData>
}

// 3. RoomHoldService (Booking Session Locking) ⭐
@Injectable({ providedIn: 'root' })
export class RoomHoldService {
  // Handle 15-minute booking sessions
  holdRooms(roomIds: number[], checkIn: Date, checkOut: Date): Observable<HoldResponse>
  releaseRooms(roomIds: number[], reason: 'payment_failed' | 'session_expired'): Observable<any>
  getRoomHoldStatus(roomId: number): Observable<HoldStatus>
  startSessionTimer(expiresAt: Date): Observable<number> // Returns remaining seconds
}

// 4. RoomTypeManagementService (Admin)
@Injectable({ providedIn: 'root' })
export class RoomTypeManagementService {
  createRoomType(payload: RoomTypeCreate): Observable<RoomTypeResponse>
  listRoomTypes(): Observable<RoomType[]>
  updateRoomType(typeId: number, payload: RoomTypeUpdate): Observable<RoomTypeResponse>
  deleteRoomType(typeId: number): Observable<any>
}

// 5. AmenityManagementService (Admin)
@Injectable({ providedIn: 'root' })
export class AmenityManagementService {
  createAmenity(name: string): Observable<AmenityResponse>
  listAmenities(): Observable<Amenity[]>
  mapAmenityToRoom(roomId: number, amenityId: number): Observable<any>
  unmapAmenityFromRoom(roomId: number, amenityId: number): Observable<any>
}
```

### 15-Minute Timer Component

```typescript
// shared/availability-timer/availability-timer.component.ts
@Component({
  selector: 'app-availability-timer',
  template: `
    <div class="timer-container" [class.warning]="remainingSeconds < 300">
      <span class="label">Session expires in:</span>
      <span class="time">{{ minutes }}:{{ seconds | pad }}</span>
      <span class="status" *ngIf="remainingSeconds < 300">⚠️ Complete payment!</span>
    </div>
  `
})
export class AvailabilityTimerComponent implements OnInit, OnDestroy {
  @Input() expiresAt: Date;
  remainingSeconds = 900; // 15 minutes
  minutes = 15;
  seconds = 0;
  private subscription: Subscription;

  ngOnInit() {
    this.subscription = interval(1000).subscribe(() => {
      const now = new Date().getTime();
      const expiry = new Date(this.expiresAt).getTime();
      this.remainingSeconds = Math.floor((expiry - now) / 1000);
      
      this.minutes = Math.floor(this.remainingSeconds / 60);
      this.seconds = this.remainingSeconds % 60;
      
      if (this.remainingSeconds <= 0) {
        this.onSessionExpired();
      }
    });
  }

  private onSessionExpired() {
    this.subscription.unsubscribe();
    // Release rooms and show notification
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
  }
}
```

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Backend APIs (2-3 hours)

```
✅ STEP 1: Add room holding/locking APIs
   File: BACKEND/app/routes/rooms.py
   ├─ POST /room-management/rooms/hold
   ├─ POST /room-management/rooms/unlock
   └─ GET /room-management/rooms/availability

✅ STEP 2: Implement holding logic in service
   File: BACKEND/app/services/rooms.py
   ├─ hold_rooms()
   ├─ unlock_rooms()
   ├─ check_availability()
   └─ expire_holds() (internal utility)

✅ STEP 3: Create scheduled worker
   File: BACKEND/app/workers/release_room_holds_worker.py
   └─ Runs every 1 minute to expire holds

✅ STEP 4: Add Redis caching for bookings
   File: BACKEND/app/core/redis_manager.py
   ├─ Store booking session with expiry
   └─ Cache availability per date range

✅ STEP 5: Database migration (if needed)
   Ensure hold_expires_at column exists
```

### Phase 2: Frontend Models & Services (1.5 hours)

```
✅ STEP 1: Create TypeScript models
   File: FRONTEND/src/app/features/rooms/models/
   ├─ room.model.ts
   ├─ room-type.model.ts
   ├─ room-availability.model.ts
   └─ booking-session.model.ts

✅ STEP 2: Implement services
   File: FRONTEND/src/app/features/rooms/services/
   ├─ room-management.service.ts (admin)
   ├─ room-availability.service.ts (search)
   ├─ room-hold.service.ts (booking sessions) ⭐
   ├─ room-type-management.service.ts
   └─ amenity-management.service.ts

✅ STEP 3: Create shared components
   File: FRONTEND/src/app/features/rooms/shared/
   ├─ availability-timer.component.ts (15-min countdown)
   ├─ room-status-badge.component.ts
   └─ room-amenities-display.component.ts
```

### Phase 3: Admin Components (2-3 hours)

```
✅ STEP 1: Room management components
   ├─ room-list.component (list, search, filter, delete)
   ├─ room-create-edit.component (create/edit form)
   ├─ room-availability-status.component (visual status)
   └─ room-type-management.component

✅ STEP 2: Amenity management
   ├─ amenity-list.component
   └─ amenity-mapper.component (map to rooms)

✅ STEP 3: Routing & integration
   └─ rooms-routing.module.ts (admin routes)
```

### Phase 4: Customer Components (2-3 hours)

```
✅ STEP 1: Room search & browsing
   ├─ room-search.component (date + filters)
   ├─ room-list-display.component (results)
   └─ room-details.component (expanded view)

✅ STEP 2: Room selection & holding
   ├─ room-selection.component (multi-select)
   ├─ room-card.component (individual card)
   └─ room-selector-modal.component (modal)

✅ STEP 3: Calendar & availability
   ├─ availability-calendar.component
   └─ date-range-picker.component

✅ STEP 4: Booking session UI
   └─ booking-session-summary.component
       ├─ Shows selected rooms
       ├─ Shows 15-min timer
       ├─ Shows total price
       └─ Proceed to payment button
```

### Phase 5: Integration & Testing (1 hour)

```
✅ STEP 1: Integrate with booking module
   └─ Connect room-hold to booking creation

✅ STEP 2: Integrate with payment module
   └─ Release rooms on payment failure
   └─ Confirm booking on payment success

✅ STEP 3: Testing
   ├─ Manual testing of hold/release
   ├─ Timer expiry simulation
   ├─ Multi-room booking
   └─ Payment failure scenario
```

---

## 📡 API ENDPOINTS REFERENCE

### Current (Existing)

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/room-management/types` | Create room type | ROOM_MANAGEMENT:WRITE |
| GET | `/room-management/types` | List room types | ROOM_MANAGEMENT:WRITE |
| PUT | `/room-management/types/{id}` | Update room type | ROOM_MANAGEMENT:WRITE |
| DELETE | `/room-management/types/{id}` | Delete room type | ROOM_MANAGEMENT:DELETE |
| POST | `/room-management/rooms` | Create room | ROOM_MANAGEMENT:WRITE |
| GET | `/room-management/rooms` | List rooms | ROOM_MANAGEMENT:WRITE |
| GET | `/room-management/rooms/{id}` | Get room | - |
| PUT | `/room-management/rooms/{id}` | Update room | ROOM_MANAGEMENT:WRITE |
| DELETE | `/room-management/rooms/{id}` | Delete room | ROOM_MANAGEMENT:DELETE |
| POST | `/room-management/types/{id}/images` | Upload image | ROOM_MANAGEMENT:WRITE |

### NEW (To Implement Tomorrow)

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/room-management/rooms/hold` | Hold rooms for booking | - |
| POST | `/room-management/rooms/unlock` | Release room hold | - |
| GET | `/room-management/rooms/availability` | Check availability | - |
| POST | `/room-management/amenities` | Create amenity | ROOM_MANAGEMENT:WRITE |
| GET | `/room-management/amenities` | List amenities | - |
| POST | `/room-management/amenities/map` | Map amenity to room | ROOM_MANAGEMENT:WRITE |
| DELETE | `/room-management/amenities/unmap` | Unmap amenity | ROOM_MANAGEMENT:WRITE |

---

## 🔄 DATA FLOW - BOOKING WITH ROOM LOCKING

### Complete Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│         COMPLETE BOOKING FLOW WITH ROOM LOCKING                    │
└────────────────────────────────────────────────────────────────────┘

CUSTOMER BROWSER
├─ [1] Check-in date picker: 2025-12-01
├─ [2] Check-out date picker: 2025-12-03
├─ [3] Adult count: 2, Child count: 0
└─ [4] Click "Search"
    │
    ▼
FRONTEND: room-search.component
├─ Call: roomAvailabilityService.getAvailableRooms(checkIn, checkOut, {adults: 2})
│
▼
BACKEND: GET /room-management/rooms/availability
├─ Query SQL (joins Bookings, Rooms, RoomTypes)
├─ Filter available rooms for date range
├─ Calculate prices for night count
├─ Include amenities & images
│
▼
FRONTEND: room-list-display.component
├─ Display available rooms with:
│  ├─ Room images
│  ├─ Room details (size, type, amenities)
│  ├─ Price per night × number of nights
│  └─ "Select" button
│
CUSTOMER SELECTS ROOMS
├─ [5] Select Room 101, Room 102, Room 103
├─ [6] Click "Add to Cart" / "Proceed to Booking"
│
▼
FRONTEND: booking-session-summary.component
├─ Store in component state:
│  └─ selectedRoomIds = [101, 102, 103]
├─ Show summary:
│  ├─ Room 101: Deluxe (2 nights × $150 = $300)
│  ├─ Room 102: Deluxe (2 nights × $150 = $300)
│  ├─ Room 103: Standard (2 nights × $100 = $200)
│  └─ Total: $800
├─ Show 15-minute timer (countdown from 15:00)
├─ Click "Proceed to Payment"
│
▼
FRONTEND: room-hold.service.holdRooms()
├─ Call: POST /room-management/rooms/hold
│  └─ Body: {
│       room_ids: [101, 102, 103],
│       check_in: "2025-12-01",
│       check_out: "2025-12-03"
│     }
│
▼
BACKEND: POST /room-management/rooms/hold (NEW)
├─ Validate rooms available for date range
├─ For each room:
│  ├─ Set room_status = HELD
│  ├─ Set freeze_reason = SYSTEM_HOLD
│  ├─ Set hold_expires_at = NOW() + 15 minutes
│  └─ Cache in Redis
├─ Response:
│  └─ {
│      successfully_held: [
│        {
│          room_id: 101,
│          held_until: "2025-11-28T14:30:45Z"
│        },
│        ...
│      ]
│    }
│
▼
FRONTEND: availability-timer.component
├─ Start countdown: 15:00 → 14:59 → ... → 0:00
├─ Show warning at 5:00 ⚠️
├─ Update every 1 second
│
CUSTOMER PROCEEDS TO PAYMENT
├─ [7] Enter payment details
├─ [8] Click "Pay Now"
│
▼
PAYMENT PROCESSING
├─ IF PAYMENT SUCCESSFUL:
│  │
│  ▼
│  FRONTEND: payment.component
│  ├─ Call: POST /bookings/create
│  │  └─ Body includes: room_ids, check_in, check_out, user_id
│  │
│  ▼
│  BACKEND: POST /bookings/create
│  ├─ Create Booking record
│  ├─ Create BookingRoomMap entries for each room
│  ├─ For each room:
│  │  ├─ Set room_status = BOOKED
│  │  ├─ Set hold_expires_at = NULL
│  │  └─ Invalidate cache
│  ├─ Return booking_id
│  │
│  ▼
│  FRONTEND: Confirmation page
│  └─ Show: "Booking confirmed! Booking ID: #12345"
│
├─ IF PAYMENT FAILED:
│  │
│  ▼
│  FRONTEND: payment-failed.component
│  ├─ Call: room-hold.service.releaseRooms()
│  │  └─ POST /room-management/rooms/unlock
│  │     └─ Body: {room_ids: [101, 102, 103], reason: "payment_failed"}
│  │
│  ▼
│  BACKEND: POST /room-management/rooms/unlock
│  ├─ For each room:
│  │  ├─ Set room_status = AVAILABLE
│  │  ├─ Set freeze_reason = NONE
│  │  ├─ Set hold_expires_at = NULL
│  │  └─ Clear from Redis cache
│  │
│  ▼
│  FRONTEND: Show error message
│  └─ "Payment failed. Rooms released. Try again."
│
└─ IF SESSION TIMEOUT (15 mins reached):
   │
   ▼
   BACKEND WORKER: release_room_holds_worker.py
   ├─ Runs every 1 minute
   ├─ Finds rooms where:
   │  ├─ room_status = HELD
   │  ├─ hold_expires_at <= NOW()
   ├─ For each:
   │  ├─ Set room_status = AVAILABLE
   │  ├─ Set hold_expires_at = NULL
   │  ├─ Log action
   │  └─ Notify customer (optional)
   │
   ▼
   FRONTEND: Timer reaches 0:00
   ├─ Show notification: "Session expired. Rooms released."
   ├─ Navigate to room search
   └─ User can start over
```

---

## 🎯 CRITICAL SUCCESS FACTORS

### ✅ Must Implement Tomorrow

1. **Room Hold API** - Lock rooms for 15 minutes with expiry timestamp
2. **Room Unlock API** - Release rooms on payment failure or timeout
3. **Availability Check** - Query available rooms for date range
4. **Session Timer** - Frontend countdown showing remaining time
5. **Scheduled Worker** - Auto-release expired holds every minute
6. **Redis Caching** - Store booking session data with TTL

### ⚠️ Common Pitfalls to Avoid

```
❌ NOT setting hold_expires_at correctly
   → Rooms won't auto-release after 15 mins

❌ NOT checking expired holds in availability query
   → Shows rooms as unavailable even after timer expires

❌ NOT handling payment failure scenario
   → Rooms stay HELD forever

❌ NOT caching booking sessions
   → Poor performance with many concurrent bookings

❌ NOT implementing scheduled worker
   → Manual database cleanup needed

❌ NOT showing timer in UI
   → Customers don't know they have 15 mins
```

### 🟢 Testing Checklist Tomorrow

```
✅ Create rooms and room types
✅ Search for available rooms (2-day range)
✅ Hold multiple rooms (test concurrency)
✅ Simulate payment success → room becomes BOOKED
✅ Simulate payment failure → room becomes AVAILABLE
✅ Wait for timer to expire → worker releases rooms
✅ Check availability query excludes HELD rooms until expiry
✅ Check Redis cache stores booking session
✅ Test multi-room bookings
✅ Test with different check-in/check-out dates
```

---

## 📞 QUICK REFERENCE

### Room Status Transitions

```
AVAILABLE ──hold──> HELD (expires_at = NOW() + 15 min)
   │                 │
   │                 ├─ payment_success ──> BOOKED (expires_at = NULL)
   │                 │
   │                 ├─ payment_failed ──> AVAILABLE (expires_at = NULL)
   │                 │
   │                 └─ timeout ──> AVAILABLE (expires_at = NULL)
   │
   └──freeze──> FROZEN (freeze_reason = ADMIN_LOCK)
```

### Key Timestamp Fields

```
hold_expires_at       → When 15-min hold expires (UTC)
check_in              → Booking check-in date
check_out             → Booking check-out date
created_at            → When room was created
updated_at            → Last update timestamp
```

### Important Scopes

```
ROOM_MANAGEMENT:READ   → View rooms
ROOM_MANAGEMENT:WRITE  → Create/update rooms
ROOM_MANAGEMENT:DELETE → Delete rooms
```

---

## 🎓 SUMMARY

**Tomorrow's Goal:** Build a complete room management system where:

1. ✅ **Admin** can manage rooms, room types, and amenities
2. ✅ **Customer** can search for available rooms by date
3. ✅ **System** holds rooms for 15 minutes during booking
4. ✅ **System** releases rooms if payment fails or timeout occurs
5. ✅ **System** auto-expires holds using background worker
6. ✅ **Frontend** shows 15-minute countdown timer
7. ✅ **Backend** validates room availability by date range

This foundation will make the booking module implementation seamless!

