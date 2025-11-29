# 🚀 ROOMS MODULE - QUICK REFERENCE CARD (1-PAGE VISUAL GUIDE)

---

## 📊 SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│  CUSTOMER SEARCHES ROOMS (Dec 1-3, 2 adults)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  GET /rooms/availability?check_in=2025-12-01&...           │
│  ✅ Returns: 5 available rooms with prices & amenities      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  CUSTOMER SELECTS: Room 101, 102, 103                        │
│  CLICKS: "Proceed to Payment"                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  POST /rooms/hold → {"room_ids": [101, 102, 103]}           │
│  ✅ Response: session_id, held_until timestamp              │
│  🗄️  Database: room_status = HELD, hold_expires_at = +15min │
│  🗂️  Redis: booking_session stored with 15-min TTL          │
│  ⏱️  Frontend: Timer starts 15:00 → 14:59 → ...             │
└─────────────────────────────────────────────────────────────┘
                            ↓ (0-15 minutes)
                    ┌───────────────┬───────────────┐
                    ↓               ↓               ↓
            ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
            │ PAYMENT       │  │ SESSION       │  │ AUTO-RELEASE  │
            │ SUCCESS       │  │ EXPIRES       │  │ (after 15min) │
            ├───────────────┤  ├───────────────┤  ├───────────────┤
            │ POST /booking │  │ Timer → 0:00  │  │ Worker runs   │
            │ /create       │  │ POST /unlock  │  │ POST /unlock  │
            │               │  │ reason:       │  │ reason:       │
            │ Rooms:        │  │ session_exp.  │  │ session_exp.  │
            │ HELD → BOOKED │  │ Rooms:        │  │ Rooms:        │
            │               │  │ HELD → AVAIL  │  │ HELD → AVAIL  │
            │ ✅ BOOKING    │  │ 🔓 RELEASED   │  │ 🔓 RELEASED   │
            │ COMPLETE      │  │               │  │ (automatic)   │
            └───────────────┘  └───────────────┘  └───────────────┘
```

---

## 🗄️ DATABASE STATE AT EACH STEP

```
STEP 1: Before holding
┌─────┬─────────┬──────────────────┐
│ ID  │ Status  │ hold_expires_at  │
├─────┼─────────┼──────────────────┤
│ 101 │ AVAILAB │ NULL             │
│ 102 │ AVAILAB │ NULL             │
│ 103 │ AVAILAB │ NULL             │
└─────┴─────────┴──────────────────┘

STEP 2: After holding (POST /rooms/hold)
┌─────┬─────────┬──────────────────┐
│ ID  │ Status  │ hold_expires_at  │
├─────┼─────────┼──────────────────┤
│ 101 │ HELD    │ 2025-11-28 14:30 │
│ 102 │ HELD    │ 2025-11-28 14:30 │
│ 103 │ HELD    │ 2025-11-28 14:30 │
└─────┴─────────┴──────────────────┘

STEP 3a: Payment SUCCESS (POST /bookings/create)
┌─────┬─────────┬──────────────────┐
│ ID  │ Status  │ hold_expires_at  │
├─────┼─────────┼──────────────────┤
│ 101 │ BOOKED  │ NULL             │ ← booking created
│ 102 │ BOOKED  │ NULL             │ ← in BookingRoomMap
│ 103 │ BOOKED  │ NULL             │
└─────┴─────────┴──────────────────┘

STEP 3b: Payment FAILED (POST /rooms/unlock)
┌─────┬─────────┬──────────────────┐
│ ID  │ Status  │ hold_expires_at  │
├─────┼─────────┼──────────────────┤
│ 101 │ AVAILAB │ NULL             │ ← released for others
│ 102 │ AVAILAB │ NULL             │
│ 103 │ AVAILAB │ NULL             │
└─────┴─────────┴──────────────────┘
```

---

## 🔧 WHAT TO BUILD - BACKEND (3 APIs + 1 Worker)

```
┌──────────────────────────────────────────────────────────────┐
│ API #1: POST /room-management/rooms/hold                     │
├──────────────────────────────────────────────────────────────┤
│ REQUEST:  { room_ids: [101,102], check_in, check_out }       │
│ RESPONSE: { successfully_held, failed, session_id }          │
│ DB QUERY: UPDATE rooms SET room_status=HELD, hold_exp=NOW+15 │
│ REDIS:    SET booking_session:{id} {...} EX 900              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ API #2: POST /room-management/rooms/unlock                   │
├──────────────────────────────────────────────────────────────┤
│ REQUEST:  { room_ids: [101,102], reason }                    │
│ RESPONSE: { successfully_released, failed }                  │
│ DB QUERY: UPDATE rooms SET room_status=AVAILABLE, hold_exp=NL│
│ REDIS:    DEL booking_session:{id}                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ API #3: GET /room-management/rooms/availability              │
├──────────────────────────────────────────────────────────────┤
│ QUERY:    check_in, check_out, adults, children              │
│ RESPONSE: { available_rooms[], unavailable_count }           │
│ DB QUERY: SELECT * WHERE status IN (AVAIL, HELD+expired)     │
│           AND (check_out <= check_in OR check_in >= check_out)
│ CACHE:    GET room_avail:{date_range} (1-min TTL)            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ WORKER: Scheduled Task (Every 1 minute)                      │
├──────────────────────────────────────────────────────────────┤
│ QUERY:   SELECT * WHERE status=HELD AND hold_expires <= NOW()│
│ ACTION:  UPDATE rooms SET status=AVAILABLE, hold_expires=NL  │
│ LOG:     "Released X rooms due to timeout"                   │
│ REPEAT:  Every 60 seconds automatically                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎨 WHAT TO BUILD - FRONTEND (Services + Components)

```
┌──────────────────────────────────────────────────────────────┐
│ SERVICE #1: RoomAvailabilityService                          │
├──────────────────────────────────────────────────────────────┤
│ getAvailableRooms(checkIn, checkOut, adults, children)       │
│   └─ GET /rooms/availability?check_in=...&check_out=...      │
│   └─ Return: AvailableRoom[]                                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SERVICE #2: RoomHoldService                                  │
├──────────────────────────────────────────────────────────────┤
│ holdRooms(roomIds, checkIn, checkOut)                        │
│   └─ POST /rooms/hold {room_ids, check_in, check_out}        │
│   └─ Return: HoldResponse with session_id & expiry           │
│                                                              │
│ releaseRooms(roomIds, reason)                                │
│   └─ POST /rooms/unlock {room_ids, reason}                   │
│   └─ Return: { successfully_released, failed }               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ COMPONENT #1: AvailabilityTimerComponent                     │
├──────────────────────────────────────────────────────────────┤
│ @Input: expiresAt (ISO timestamp)                            │
│ Display: 14:59 → 14:58 → ... → 5:00 (warning) → 0:00        │
│ Emit: sessionExpired event at 0:00                           │
│ Update: Every 1000ms (1 second)                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ COMPONENT #2: RoomSearchComponent                            │
├──────────────────────────────────────────────────────────────┤
│ Form: check_in, check_out, adults, children                  │
│ On Submit: Call roomAvailabilityService.getAvailableRooms()  │
│ Display: List of available rooms with prices                 │
│ Select: Pass selected room IDs to parent                     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ COMPONENT #3: RoomSelectionComponent                         │
├──────────────────────────────────────────────────────────────┤
│ Input: selected rooms array                                  │
│ Display: Summary with total price                            │
│ Button: "Proceed to Payment" (calls hold service)            │
│ On Hold Success: Show timer & lock UI                        │
│ On Hold Failure: Show error & release rooms                  │
└──────────────────────────────────────────────────────────────┘
```

---

## ⏱️ TIMING DIAGRAM

```
T=0:00   Customer browsing
         ↓
T=0:05   Customer selects room 101, 102, 103
         ↓
T=0:06   POST /rooms/hold
         Rooms status: AVAILABLE → HELD
         DB: hold_expires_at = 14:06 UTC
         Redis: booking_session stored
         Frontend: Timer shows 14:54
         ↓
T=0:10   Customer fills payment form
         ↓
T=0:12   Customer clicks "Pay Now"
         ↓
T=0:13   Payment gateway processing
         ↓
         ╔═════════════════════════════════════╗
         ║ IF PAYMENT SUCCESS (T=0:14):         ║
         ║   POST /bookings/create               ║
         ║   Rooms: HELD → BOOKED                ║
         ║   Result: ✅ Booking complete         ║
         ║                                       ║
         ║ IF PAYMENT FAILED (T=0:14):           ║
         ║   POST /rooms/unlock                  ║
         ║   Rooms: HELD → AVAILABLE             ║
         ║   Result: ❌ Error message            ║
         ║                                       ║
         ║ IF TIMEOUT (T=14:06):                 ║
         ║   Worker automatically runs           ║
         ║   Rooms: HELD → AVAILABLE             ║
         ║   Result: Session expired notice      ║
         ╚═════════════════════════════════════╝
```

---

## 🎯 MUST-DO CHECKLIST

### Backend
- [ ] Create POST /rooms/hold endpoint
- [ ] Create POST /rooms/unlock endpoint
- [ ] Create GET /rooms/availability endpoint
- [ ] Create scheduled worker task
- [ ] Add Redis caching
- [ ] Add database indexes
- [ ] Test all 3 APIs in Postman
- [ ] Verify worker runs every 1 minute

### Frontend
- [ ] Create RoomAvailabilityService
- [ ] Create RoomHoldService
- [ ] Create AvailabilityTimerComponent
- [ ] Create RoomSearchComponent
- [ ] Create RoomSelectionComponent
- [ ] Wire up to existing auth
- [ ] Test full flow manually
- [ ] Handle all error scenarios

### Database
- [ ] Verify hold_expires_at column exists
- [ ] Add index on room_status + hold_expires_at
- [ ] Test database transactions
- [ ] Backup before changes
- [ ] Verify constraints

### Testing
- [ ] Single room hold/unlock
- [ ] Multi-room hold/unlock
- [ ] Timer countdown (use 2-min TTL for testing)
- [ ] Availability query with various dates
- [ ] Payment success flow
- [ ] Payment failure flow
- [ ] Session timeout (wait 15 mins or use short TTL)
- [ ] Error scenarios (invalid dates, booked rooms, etc.)

---

## 📊 KEY NUMBERS

```
Session Duration: 15 minutes (900 seconds)
Hold TTL: 900 seconds (matches session)
Worker Frequency: Every 60 seconds
Availability Cache TTL: 60 seconds
Room Types Cache TTL: 300 seconds
Timer Update Frequency: Every 1000ms
Booking Session TTL: 900 seconds
```

---

## 🔒 ROOM STATUS REFERENCE

```
AVAILABLE   → Ready for booking (normal state)
HELD        → Temporarily locked for 15 mins (booking in progress)
BOOKED      → Currently occupied (checkout date passed → AVAILABLE)
MAINTENANCE → Admin lock for cleaning (need manual unlock)
FROZEN      → Admin lock (admin_lock reason)
```

---

## 🚨 ERROR SCENARIOS TO HANDLE

```
❌ Room already booked for dates
   → Return failed with reason

❌ Room in MAINTENANCE or FROZEN state
   → Return failed with reason

❌ Invalid date range (checkout ≤ checkin)
   → Validate in form & API

❌ Session expired during payment
   → Show "Session expired" message

❌ Payment failed
   → Immediately call POST /rooms/unlock

❌ Occupancy mismatch
   → Validate max_adult_count & max_child_count

❌ Redis cache miss
   → Query database directly

❌ Database transaction fails
   → Rollback & return error
```

---

## ✅ DAY 2 SUCCESS CRITERIA

```
✅ Hold 3 rooms via Postman
✅ Unlock rooms via Postman
✅ Search available rooms (various dates)
✅ Timer counts down from 15:00
✅ Rooms auto-release after 15 mins (worker)
✅ Multi-room booking works
✅ Payment success → BOOKED state
✅ Payment failure → AVAILABLE state
✅ All error scenarios handled
✅ Ready for booking module integration
```

---

## 📚 REFERENCE FILES TO LOOK AT

```
Backend:
├─ app/routes/authentication.py (for route structure)
├─ app/services/bookings_service.py (for service pattern)
├─ app/crud/rooms.py (for database helper pattern)
└─ app/core/cache.py (for Redis usage)

Frontend:
├─ core/services/permissions/permissions.ts (for service pattern)
├─ core/guards/auth.guard.ts (for guard pattern)
└─ core/directives/has-permission.directive.ts (for RxJS pattern)
```

---

**Print this card & keep it on your desk while coding! 🎯**

