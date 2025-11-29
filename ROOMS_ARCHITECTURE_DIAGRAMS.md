# 🏨 ROOMS MODULE - VISUAL ARCHITECTURE & INTEGRATION DIAGRAMS

---

## 📐 SYSTEM ARCHITECTURE - LAYERS

```
┌─────────────────────────────────────────────────────────────────┐
│                         CUSTOMER BROWSER                         │
├─────────────────────────────────────────────────────────────────┤
│
│  ANGULAR FRONTEND (rooms-management module)
│  ├─ room-search.component
│  ├─ room-selection.component
│  ├─ availability-timer.component
│  ├─ booking-session-summary.component
│  └─ Payment integration point
│
├─────────────────────────────────────────────────────────────────┤
│
│  HTTP/REST API Layer
│  ├─ Authorization: Bearer Token (JWT)
│  ├─ CORS: enabled for frontend domain
│  └─ Content-Type: application/json
│
├─────────────────────────────────────────────────────────────────┤
│
│  FASTAPI BACKEND (Python)
│  │
│  ├─ Routes Layer (rooms.py)
│  │  ├─ POST   /room-management/rooms/hold
│  │  ├─ POST   /room-management/rooms/unlock
│  │  ├─ GET    /room-management/rooms/availability
│  │  ├─ POST   /room-management/rooms
│  │  ├─ PUT    /room-management/rooms/{id}
│  │  └─ DELETE /room-management/rooms/{id}
│  │
│  ├─ Services Layer (services/rooms.py)
│  │  ├─ hold_rooms(db, room_ids, check_in, check_out)
│  │  ├─ unlock_rooms(db, room_ids, reason)
│  │  ├─ check_availability(db, check_in, check_out, filters)
│  │  └─ expire_holds(db)
│  │
│  ├─ Dependencies Layer
│  │  ├─ get_current_user (from token)
│  │  └─ check_permission (scope validation)
│  │
│  └─ Workers Layer (background tasks)
│     └─ release_room_holds_worker.py (every 1 min)
│
├─────────────────────────────────────────────────────────────────┤
│
│  CACHING Layer
│  ├─ Redis Cluster
│  │  ├─ Cache: booking_session:{session_id}
│  │  ├─ Cache: room_types:* (5 min TTL)
│  │  └─ Cache: room_availability:{date_range} (1 min TTL)
│  │
│  └─ In-Memory Cache (SQLAlchemy)
│     └─ ORM query caching
│
├─────────────────────────────────────────────────────────────────┤
│
│  DATA Layer (PostgreSQL)
│  ├─ rooms table
│  ├─ room_types table
│  ├─ bookings table
│  ├─ booking_room_map table
│  ├─ room_amenities table
│  └─ room_amenity_map table
│
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 REQUEST/RESPONSE FLOW - ROOM AVAILABILITY CHECK

```
TIME: T=0ms
┌──────────────┐
│  CUSTOMER    │ "I want to stay Dec 1-3, 2 adults"
│  BROWSER     │
└──────┬───────┘
       │ GET /room-management/rooms/availability?check_in=2025-12-01&check_out=2025-12-03&adults=2
       │
       ▼
┌──────────────────────────────┐
│  ANGULAR Frontend            │
│  room-search.component       │
│  ├─ Parse input dates        │
│  ├─ Call service             │
│  ├─ Show loading spinner     │
│  └─ Validate input           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  HTTP Client                 │
│  ├─ Add JWT token            │
│  ├─ Set headers              │
│  └─ Build query params       │
└──────┬───────────────────────┘
       │ Request sent to backend
       │
       ▼ TIME: T=5ms
┌──────────────────────────────┐
│  FastAPI Route Handler       │
│  GET /room-management/       │
│      rooms/availability      │
│  ├─ Validate token           │
│  ├─ Extract params           │
│  └─ Call service layer       │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Service Layer               │
│  check_availability()        │
│  ├─ Parse dates              │
│  ├─ Apply filters            │
│  └─ Call CRUD layer          │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=10ms
┌──────────────────────────────┐
│  Database Query (PostgreSQL) │
│  SELECT * FROM rooms         │
│  WHERE room_status IN        │
│    ('AVAILABLE', 'HELD')     │
│  AND hold_expires_at > NOW() │
│  AND (check_in conflicts)    │
│  LEFT JOIN bookings...       │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=40ms (with joins)
┌──────────────────────────────┐
│  SQL Result Set              │
│  ├─ room_id: [101, 102, 103] │
│  ├─ room_type info           │
│  └─ amenities & images       │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Service Layer               │
│  ├─ Serialize results        │
│  ├─ Calculate prices         │
│  ├─ Add amenities            │
│  └─ Build response           │
└──────┬───────────────────────┘
       │ JSON Response
       │ Status: 200 OK
       │
       ▼ TIME: T=50ms
┌──────────────────────────────┐
│  HTTP Client (Angular)       │
│  ├─ Receive response         │
│  ├─ Parse JSON               │
│  └─ Pass to component        │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  room-list-display.component │
│  ├─ Map response data        │
│  ├─ Render room cards        │
│  └─ Show amenities & images  │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=60ms
┌──────────────────────────────┐
│  DOM Rendered                │
│  ├─ Room 101 card            │
│  ├─ Room 102 card            │
│  └─ Room 103 card            │
│  Each with:                  │
│  ├─ Price/night × nights     │
│  ├─ Amenity badges           │
│  ├─ Images carousel          │
│  └─ "Select" button          │
└──────────────────────────────┘

TOTAL TIME: 60ms
```

---

## 🔐 REQUEST/RESPONSE FLOW - ROOM LOCKING (HOLD)

```
CUSTOMER CLICKS "Proceed to Payment"
│
├─ Room IDs: [101, 102, 103]
├─ Check-in: 2025-12-01
├─ Check-out: 2025-12-03
│
▼ TIME: T=0ms
┌──────────────────────────────┐
│  FRONTEND: room-hold.service │
│  holdRooms(                  │
│    [101,102,103],            │
│    2025-12-01,               │
│    2025-12-03]               │
│  )                           │
└──────┬───────────────────────┘
       │ POST /room-management/rooms/hold
       │ Body: {
       │   "room_ids": [101, 102, 103],
       │   "check_in": "2025-12-01",
       │   "check_out": "2025-12-03"
       │ }
       │
       ▼ TIME: T=5ms
┌──────────────────────────────┐
│  BACKEND: Route Handler      │
│  @router.post("/rooms/hold") │
│  ├─ Validate token           │
│  ├─ Validate dates           │
│  └─ Call service             │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  SERVICE: hold_rooms()       │
│  for each room_id:           │
│  ├─ Check current status     │
│  │  └─ Must be AVAILABLE     │
│  │                            │
│  ├─ Query bookings           │
│  │  └─ No overlaps?          │
│  │                            │
│  ├─ Set:                     │
│  │  ├─ room_status=HELD      │
│  │  ├─ freeze_reason=        │
│  │  │   SYSTEM_HOLD          │
│  │  └─ hold_expires_at=      │
│  │      NOW()+15min          │
│  │                            │
│  └─ Add to Redis cache       │
└──────┬───────────────────────┘
       │ (for each room: 2 DB updates)
       │
       ▼ TIME: T=20ms
┌──────────────────────────────┐
│  Database Updated            │
│                              │
│  Before:                     │
│  ┌──────────────────┐        │
│  │ room_id  │status │        │
│  ├──────────┼────── │        │
│  │   101    │AVAIL. │        │
│  │   102    │AVAIL. │        │
│  │   103    │AVAIL. │        │
│  └──────────────────┘        │
│                              │
│  After:                      │
│  ┌──────────────────────┐    │
│  │ room_id │status│exp. │    │
│  ├─────────┼──────┼────│    │
│  │   101   │HELD  │14:3│    │
│  │   102   │HELD  │14:3│    │
│  │   103   │HELD  │14:3│    │
│  └──────────────────────┘    │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=25ms
┌──────────────────────────────┐
│  Redis Cache Updated         │
│  Set:                        │
│  booking_session:{session_id}│
│  {                           │
│    user_id: 1,              │
│    room_ids: [101,102,103], │
│    held_at: NOW(),          │
│    expires_at: NOW()+15min, │
│    check_in: "2025-12-01",  │
│    check_out: "2025-12-03", │
│    rooms: [                 │
│      {                      │
│        room_id: 101,        │
│        room_no: "101",      │
│        price: $150/night,   │
│        nights: 2,           │
│        total: $300          │
│      },...                  │
│    ],                       │
│    total: $800              │
│  }                          │
│  TTL: 900 seconds (15 min)  │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=30ms
┌──────────────────────────────┐
│  Response to Frontend        │
│  Status: 200 OK              │
│  {                           │
│    "successfully_held": [    │
│      {                       │
│        "room_id": 101,       │
│        "held_until":         │
│          "2025-11-28T...Z"   │
│      },                      │
│      ...                     │
│    ],                        │
│    "failed": []              │
│  }                           │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=35ms
┌──────────────────────────────┐
│  FRONTEND: availability-timer│
│  .component                  │
│  ├─ Parse expiresAt timestamp│
│  ├─ Start interval(1000ms)   │
│  ├─ Update every second      │
│  ├─ Show: "14:59"            │
│  ├─ Show: "14:58"            │
│  │ ...                       │
│  ├─ Show: "5:00" (warning)   │
│  │ ...                       │
│  └─ Show: "0:00" (expired)   │
│     └─ Trigger release       │
│        if payment incomplete │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=40ms
┌──────────────────────────────┐
│  UI Displays                 │
│  ├─ Booking Summary Card     │
│  ├─ Room selections shown    │
│  ├─ Timer: 14:59             │
│  ├─ Total: $800              │
│  └─ "Pay Now" button enabled │
└──────────────────────────────┘

TOTAL TIME: 40ms (+ real-time timer)
```

---

## 💳 REQUEST/RESPONSE FLOW - PAYMENT SUCCESS → BOOKING

```
CUSTOMER ENTERS PAYMENT & CLICKS "PAY"
│
▼
┌──────────────────────────────┐
│  payment.component           │
│  ├─ Validate payment form    │
│  ├─ Call payment.service     │
│  └─ Show processing spinner  │
└──────┬───────────────────────┘
       │ POST /payments/process
       │ Body: {
       │   "room_ids": [101, 102, 103],
       │   "amount": 800.00,
       │   "payment_method": "credit_card",
       │   ...
       │ }
       │
       ▼
┌──────────────────────────────┐
│  PAYMENT GATEWAY             │
│  (Stripe/Razorpay/etc)       │
│  ├─ Validate card            │
│  ├─ Charge amount            │
│  └─ Return success/failure   │
└──────┬───────────────────────┘
       │ Response: SUCCESS
       │
       ▼ TIME: T=0ms
┌──────────────────────────────┐
│  BACKEND: POST /bookings/    │
│  create                      │
│  Body: {                     │
│    user_id: 1,              │
│    room_ids: [101,102,103], │
│    check_in: "2025-12-01",  │
│    check_out: "2025-12-03", │
│    total_price: 800.00,     │
│    status: "Confirmed"      │
│  }                          │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=5ms
┌──────────────────────────────┐
│  SERVICE: create_booking()   │
│                              │
│  1. Create Bookings record:  │
│     INSERT INTO bookings     │
│     VALUES (...)             │
│     └─ booking_id returned   │
│                              │
│  2. Create BookingRoomMap:   │
│     for each room_id:        │
│     INSERT INTO              │
│     booking_room_map         │
│     (booking_id, room_id,..)│
│                              │
│  3. Update Rooms status:     │
│     for each room_id:        │
│     UPDATE rooms SET         │
│     room_status = 'BOOKED',  │
│     hold_expires_at = NULL   │
│                              │
│  4. Clear Redis:             │
│     DELETE booking_session   │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=40ms
┌──────────────────────────────┐
│  Database State After        │
│                              │
│  Bookings:                   │
│  ┌────────────────────────┐  │
│  │ booking_id │ user │chk┃ │
│  │ (NEW) 5432 │ 1    │  1│  │
│  └────────────────────────┘  │
│                              │
│  BookingRoomMap:             │
│  ┌──────────────────────┐    │
│  │ booking │ room │type │    │
│  │ 5432    │ 101  │ 1   │    │
│  │ 5432    │ 102  │ 1   │    │
│  │ 5432    │ 103  │ 2   │    │
│  └──────────────────────┘    │
│                              │
│  Rooms:                      │
│  ┌────────────────────┐      │
│  │ room │ status │exp │      │
│  │ 101  │ BOOKED │ NL │      │
│  │ 102  │ BOOKED │ NL │      │
│  │ 103  │ BOOKED │ NL │      │
│  └────────────────────┘      │
└──────┬───────────────────────┘
       │ Response to Payment Service
       │ {
       │   "booking_id": 5432,
       │   "status": "Confirmed"
       │ }
       │
       ▼ TIME: T=50ms
┌──────────────────────────────┐
│  payment.service             │
│  ├─ Receive booking_id       │
│  └─ Return to component      │
└──────┬───────────────────────┘
       │ Response: {booking_id: 5432}
       │
       ▼
┌──────────────────────────────┐
│  payment.component           │
│  ├─ Stop timer               │
│  ├─ Hide spinner             │
│  ├─ Store booking_id in state│
│  └─ Navigate to confirmation │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=60ms
┌──────────────────────────────┐
│  confirmation.component      │
│  ├─ Show "Success!" message  │
│  ├─ Display booking_id: 5432 │
│  ├─ Show booked rooms        │
│  ├─ Show check-in/out dates  │
│  ├─ Show total: $800         │
│  └─ "View Booking" button    │
└──────────────────────────────┘

✅ BOOKING COMPLETE - ROOMS LOCKED PERMANENTLY
```

---

## ❌ REQUEST/RESPONSE FLOW - PAYMENT FAILURE → UNLOCK

```
PAYMENT GATEWAY RETURNS: FAILURE (Card declined)
│
▼ TIME: T=0ms
┌──────────────────────────────┐
│  payment.component           │
│  ├─ Catch error              │
│  ├─ Receive error message    │
│  └─ Show error notification  │
└──────┬───────────────────────┘
       │ Call: room-hold.service.releaseRooms()
       │
       ▼
┌──────────────────────────────┐
│  room-hold.service           │
│  releaseRooms(               │
│    [101, 102, 103],          │
│    'payment_failed'          │
│  )                           │
└──────┬───────────────────────┘
       │ POST /room-management/rooms/unlock
       │ Body: {
       │   "room_ids": [101, 102, 103],
       │   "reason": "payment_failed"
       │ }
       │
       ▼ TIME: T=5ms
┌──────────────────────────────┐
│  BACKEND: POST              │
│  /room-management/rooms/    │
│  unlock                     │
│  ├─ Validate request        │
│  └─ Call service            │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  SERVICE: unlock_rooms()     │
│  for each room_id:           │
│  ├─ Query current status     │
│  │  └─ Must be HELD          │
│  │                            │
│  ├─ Update:                  │
│  │  ├─ room_status=AVAILABLE │
│  │  ├─ freeze_reason=NONE    │
│  │  ├─ hold_expires_at=NULL  │
│  │                            │
│  ├─ Clear from Redis         │
│  │  └─ DEL booking_session   │
│  │                            │
│  └─ Log audit event          │
│     └─ "payment_failed"      │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=15ms
┌──────────────────────────────┐
│  Database Updated            │
│                              │
│  Before:                     │
│  ┌──────────────────┐        │
│  │ room │ status│exp│        │
│  │ 101  │ HELD  │..│        │
│  │ 102  │ HELD  │..│        │
│  │ 103  │ HELD  │..│        │
│  └──────────────────┘        │
│                              │
│  After:                      │
│  ┌──────────────────┐        │
│  │ room │status│exp │       │
│  │ 101  │AVAIL.│NLL│       │
│  │ 102  │AVAIL.│NLL│       │
│  │ 103  │AVAIL.│NLL│       │
│  └──────────────────┘        │
└──────┬───────────────────────┘
       │ Response to Frontend
       │ {
       │   "successfully_released": [101,102,103],
       │   "failed": []
       │ }
       │
       ▼ TIME: T=25ms
┌──────────────────────────────┐
│  FRONTEND: room-hold.service │
│  ├─ Receive response         │
│  └─ Emit event               │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  payment.component           │
│  ├─ Stop timer               │
│  ├─ Show error message:      │
│  │  "Payment failed"         │
│  │  "Rooms released"         │
│  │  "Try again or restart"   │
│  ├─ Disable "Try Again"      │
│  │  for 2 seconds            │
│  └─ Enable "Back to Search"  │
│     button                   │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=30ms
┌──────────────────────────────┐
│  UI Shows Error              │
│  ├─ Red error banner         │
│  ├─ Message: Payment failed  │
│  ├─ Rooms are now available  │
│  ├─ "Try Again" button       │
│  └─ "Back to Search" button  │
└──────────────────────────────┘

✅ ROOMS UNLOCKED - AVAILABLE AGAIN FOR OTHER CUSTOMERS
```

---

## ⏰ SESSION TIMEOUT FLOW - AUTO-RELEASE

```
TIMER REACHES 0:00
│ (Customer didn't complete payment in 15 minutes)
│
▼ (On customer's browser)
┌──────────────────────────────┐
│  availability-timer.component│
│  ├─ remainingSeconds = 0     │
│  ├─ ngAfterViewInit:         │
│  │  this.onSessionExpired()  │
│  │                            │
│  └─ Shows notification:      │
│     "Session Expired"        │
│     "Rooms released"         │
└──────┬───────────────────────┘
       │ Call: room-hold.service.releaseRooms()
       │ (same as payment failure)
       │
       ▼ (On backend - Background Worker)
┌──────────────────────────────┐
│  SCHEDULED WORKER            │
│  (runs every 1 minute)       │
│  /app/workers/               │
│  release_room_holds_worker.py│
│                              │
│  Query:                      │
│  SELECT * FROM rooms         │
│  WHERE room_status = 'HELD'  │
│  AND hold_expires_at <= NOW()│
│                              │
│  Result: [101, 102, 103]     │
└──────┬───────────────────────┘
       │ for each room_id:
       │
       ▼
┌──────────────────────────────┐
│  UPDATE rooms SET            │
│  room_status = 'AVAILABLE',  │
│  freeze_reason = NULL,       │
│  hold_expires_at = NULL      │
│  WHERE room_id = X           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Log Action                  │
│  ├─ Entity: room             │
│  ├─ Action: unlock           │
│  ├─ Reason: session_timeout  │
│  ├─ Timestamp: NOW()         │
│  └─ Room IDs: [101,102,103]  │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Notify Customer (Optional)  │
│  POST /notifications/send    │
│  Body: {                     │
│    user_id: 1,              │
│    message: "Session exp"    │
│  }                          │
└──────┬───────────────────────┘
       │
       ▼ TIME: T=1 minute after expiry
┌──────────────────────────────┐
│  Database State              │
│                              │
│  Before (at 14:30:45):       │
│  ┌──────────────────────┐    │
│  │ room │ status │ exp │     │
│  │ 101  │ HELD   │14:30│     │
│  │ 102  │ HELD   │14:30│     │
│  │ 103  │ HELD   │14:30│     │
│  └──────────────────────┘    │
│                              │
│  After (at 14:31):           │
│  ┌──────────────────────┐    │
│  │ room │status  │ exp  │    │
│  │ 101  │AVAILABLE│ NULL │   │
│  │ 102  │AVAILABLE│ NULL │   │
│  │ 103  │AVAILABLE│ NULL │   │
│  └──────────────────────┘    │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Other Customers Can Now     │
│  See These Rooms Available   │
│  in Their Search Results     │
└──────────────────────────────┘

✅ AUTOMATIC CLEANUP - NO MANUAL INTERVENTION NEEDED
```

---

## 📊 DATABASE STATE TRANSITIONS

```
┌─────────────────────────────────────────────────────────────┐
│         ROOMS TABLE STATE CHANGES DURING BOOKING            │
└─────────────────────────────────────────────────────────────┘

State 1: INITIAL (Admin creates room)
┌─────────────────────────────────────────────────────────────┐
│ room_id │ room_no │ room_status │ freeze_reason │ hold_exp. │
├─────────┼─────────┼─────────────┼───────────────┼───────────┤
│   101   │  "101"  │ AVAILABLE   │    NONE       │   NULL    │
│   102   │  "102"  │ AVAILABLE   │    NONE       │   NULL    │
│   103   │  "103"  │ AVAILABLE   │    NONE       │   NULL    │
└─────────────────────────────────────────────────────────────┘

↓ Customer selects room & proceeds to payment

State 2: HOLD (in POST /rooms/hold)
┌─────────────────────────────────────────────────────────────┐
│ room_id │ room_no │ room_status │ freeze_reason │ hold_exp. │
├─────────┼─────────┼─────────────┼───────────────┼───────────┤
│   101   │  "101"  │ HELD        │ SYSTEM_HOLD   │ 14:30:45  │
│   102   │  "102"  │ HELD        │ SYSTEM_HOLD   │ 14:30:45  │
│   103   │  "103"  │ HELD        │ SYSTEM_HOLD   │ 14:30:45  │
└─────────────────────────────────────────────────────────────┘

        ↙ Payment Success          ↘ Payment Failed
                                    or Timeout

State 3a: BOOKED (if success)    State 3b: AVAILABLE (if fail/timeout)
┌──────────────────────────┐    ┌──────────────────────────┐
│room│status │ hold_exp   │    │room│status     │hold_exp  │
├────┼────────┼────────────┤    ├────┼───────────┼──────────┤
│101 │ BOOKED │    NULL    │    │101 │ AVAILABLE │   NULL   │
│102 │ BOOKED │    NULL    │    │102 │ AVAILABLE │   NULL   │
│103 │ BOOKED │    NULL    │    │103 │ AVAILABLE │   NULL   │
└──────────────────────────┘    └──────────────────────────┘

   ↓ Check-out date passes
   
State 4: AVAILABLE (after checkout/cancellation)
┌──────────────────────────────────────────────────┐
│ room_id │ room_status │ freeze_reason │ hold_exp │
├─────────┼─────────────┼───────────────┼──────────┤
│   101   │ AVAILABLE   │    NONE       │   NULL   │
│   102   │ AVAILABLE   │    NONE       │   NULL   │
│   103   │ AVAILABLE   │    NONE       │   NULL   │
└──────────────────────────────────────────────────┘
```

---

## 📱 FRONTEND COMPONENT INTERACTION DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    ANGULAR COMPONENTS                        │
└─────────────────────────────────────────────────────────────┘

room-search.component
├─ Date inputs (check-in, check-out)
├─ Adult/child count inputs
├─ Search button
└─ Emits: searchRequest event
   │
   ▼
room-availability.service
├─ GET /room-management/rooms/availability
├─ Parse response
└─ Return: Observable<Room[]>
   │
   ▼
room-list-display.component
├─ Receives: room array from service
├─ Maps data to room cards
├─ Renders each room with:
│  ├─ room-card.component (individual room)
│  ├─ amenity display
│  └─ images carousel
├─ Click "Select" → add to cart
└─ Click "Proceed" → emit to parent
   │
   ▼
booking-session-summary.component
├─ Receives: selected room IDs array
├─ Shows summary:
│  ├─ Room details
│  ├─ Total price
│  └─ availability-timer.component (15-min countdown)
├─ "Proceed to Payment" button
└─ Calls: room-hold.service.holdRooms()
   │
   ▼
room-hold.service
├─ POST /room-management/rooms/hold
├─ Receives: HoldResponse with expiry time
└─ Emits: holdSuccessful event
   │
   ▼
availability-timer.component
├─ Receives: expiresAt timestamp
├─ Starts interval(1000) for countdown
├─ Updates display every second
├─ Warns when < 5 minutes
└─ Calls onSessionExpired() at 0:00
   │
   ▼
payment.component
├─ Receives: selected rooms + hold confirmation
├─ Payment form inputs
├─ "Pay Now" button
├─ On Success → POST /bookings/create
│  └─ confirmation.component (success)
└─ On Failure → POST /rooms/unlock
   └─ payment-failed.component (error retry)
```

---

## 🗄️ REDIS CACHE STRUCTURE

```
Key Pattern: booking_session:{session_id}
Value Type: JSON (Hash)
TTL: 900 seconds (15 minutes) - AUTO EXPIRY

Example Entry:
─────────────────────────────────────────────────────

Key: booking_session:sess_abc123xyz

Value (JSON):
{
  "user_id": 1,
  "session_id": "sess_abc123xyz",
  "held_at": "2025-11-28T14:15:45Z",
  "expires_at": "2025-11-28T14:30:45Z",
  
  "check_in": "2025-12-01",
  "check_out": "2025-12-03",
  "nights": 2,
  
  "rooms": [
    {
      "room_id": 101,
      "room_no": "101",
      "room_type_id": 1,
      "room_type_name": "Deluxe",
      "price_per_night": 150.00,
      "nights": 2,
      "room_total": 300.00,
      "amenities": ["WiFi", "AC", "TV", "Mini Bar"]
    },
    {
      "room_id": 102,
      "room_no": "102",
      "room_type_id": 1,
      "room_type_name": "Deluxe",
      "price_per_night": 150.00,
      "nights": 2,
      "room_total": 300.00,
      "amenities": ["WiFi", "AC", "TV", "Mini Bar"]
    },
    {
      "room_id": 103,
      "room_no": "103",
      "room_type_id": 2,
      "room_type_name": "Standard",
      "price_per_night": 100.00,
      "nights": 2,
      "room_total": 200.00,
      "amenities": ["WiFi", "AC"]
    }
  ],
  
  "total_rooms": 3,
  "subtotal": 800.00,
  "taxes": 120.00,
  "total_price": 920.00,
  
  "payment_status": "pending",
  "payment_method": null,
  "payment_intent_id": null
}

Expiry: AUTO (Redis TTL handles it)
├─ Set when holding rooms
├─ Deletes at: 14:30:45 (15 min from hold time)
└─ Can manually delete on booking success
```

---

## 🔄 API RESPONSE EXAMPLES

### GET /room-management/rooms/availability

```json
{
  "available_rooms": [
    {
      "room_id": 101,
      "room_no": "101",
      "room_type_id": 1,
      "room_type": {
        "room_type_id": 1,
        "type_name": "Deluxe Suite",
        "max_adult_count": 2,
        "max_child_count": 1,
        "price_per_night": 150.00,
        "square_ft": 500,
        "description": "Spacious room with sea view"
      },
      "amenities": [
        {
          "amenity_id": 1,
          "amenity_name": "WiFi"
        },
        {
          "amenity_id": 2,
          "amenity_name": "Air Conditioning"
        }
      ],
      "images": [
        {
          "image_id": 10,
          "image_url": "https://cdn.example.com/room101_1.jpg",
          "is_primary": true,
          "caption": "Main view"
        }
      ],
      "check_in": "2025-12-01",
      "check_out": "2025-12-03",
      "nights": 2,
      "total_price": 300.00
    }
  ],
  "unavailable_count": 2,
  "total_available": 1,
  "filters_applied": {
    "check_in": "2025-12-01",
    "check_out": "2025-12-03",
    "adult_count": 2,
    "child_count": 0
  }
}
```

### POST /room-management/rooms/hold

```json
{
  "successfully_held": [
    {
      "room_id": 101,
      "room_no": "101",
      "held_until": "2025-11-28T14:30:45Z",
      "room_type_id": 1
    }
  ],
  "failed": [
    {
      "room_id": 104,
      "reason": "Room already booked for these dates"
    }
  ],
  "session_id": "sess_abc123xyz",
  "total_price": 300.00,
  "message": "Rooms held successfully. You have 15 minutes to complete payment."
}
```

### POST /room-management/rooms/unlock

```json
{
  "successfully_released": [101, 102, 103],
  "failed": [],
  "reason": "payment_failed",
  "message": "Rooms have been released and are now available again."
}
```

---

## 🎯 SUMMARY MATRIX

```
┌──────────────────────────────────────────────────────────────┐
│ FEATURE          │ IMPLEMENTATION │ COMPLEXITY │ PRIORITY   │
├──────────────────┼────────────────┼────────────┼────────────┤
│ Hold API         │ Backend        │ MEDIUM     │ CRITICAL   │
│ Unlock API       │ Backend        │ MEDIUM     │ CRITICAL   │
│ Availability API │ Backend        │ HIGH       │ CRITICAL   │
│ Hold Expiry Work │ Backend        │ MEDIUM     │ CRITICAL   │
│ Redis Caching    │ Backend        │ MEDIUM     │ HIGH       │
│ Timer Component  │ Frontend       │ LOW        │ HIGH       │
│ Search Component │ Frontend       │ MEDIUM     │ HIGH       │
│ Selection UI     │ Frontend       │ MEDIUM     │ MEDIUM     │
│ Payment Integrtn │ Full Stack     │ HIGH       │ CRITICAL   │
│ Admin Mgmt UI    │ Frontend       │ MEDIUM     │ MEDIUM     │
└──────────────────────────────────────────────────────────────┘
```

