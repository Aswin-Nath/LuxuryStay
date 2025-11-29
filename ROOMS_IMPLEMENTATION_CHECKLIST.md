# 🚀 ROOMS MANAGEMENT - IMPLEMENTATION CHECKLIST (DAY 2)

**Target Completion Time:** 8 hours  
**Session Type:** Booking + Payment within 15 minutes  
**Start Date:** November 29, 2025  

---

## 📋 QUICK START CHECKLIST

### Morning Session: Backend APIs (3-4 hours)

#### ✅ BACKEND SETUP
- [ ] Create `BACKEND/app/routes/rooms_hold.py` (new file for hold/unlock/availability endpoints)
- [ ] Or add to existing `BACKEND/app/routes/rooms.py`
- [ ] Create `BACKEND/app/services/room_hold_service.py` (business logic)
- [ ] Create `BACKEND/app/workers/release_room_holds_worker.py` (scheduler)

#### ✅ IMPLEMENT: POST /room-management/rooms/hold

**File:** `BACKEND/app/routes/rooms.py` (add new route)

```python
@router.post("/rooms/hold", status_code=status.HTTP_200_OK)
async def hold_rooms(
    payload: RoomHoldRequest,  # Pydantic model (see models section)
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Hold multiple rooms for a booking session (15 minutes)
    
    Args:
        payload.room_ids: List of room IDs to hold
        payload.check_in: Check-in date
        payload.check_out: Check-out date
    
    Returns:
        HoldResponse with successfully_held and failed lists
    """
    result = await hold_rooms_service(db, payload, current_user.user_id)
    return result
```

**Pydantic Model to Add:**
```python
# BACKEND/app/schemas/pydantic_models/room.py (add)

class RoomHoldRequest(BaseModel):
    room_ids: List[int] = Field(..., min_items=1)
    check_in: date
    check_out: date
    
    @field_validator('check_out')
    def validate_dates(cls, v, info):
        if v <= info.data.get('check_in'):
            raise ValueError("check_out must be after check_in")
        return v

class HoldResponse(BaseModel):
    successfully_held: List[dict] = []
    failed: List[dict] = []
    session_id: str
    total_price: float
    message: str
```

**Service Logic:**
```python
# BACKEND/app/services/room_hold_service.py (new file)

async def hold_rooms_service(db: AsyncSession, payload: RoomHoldRequest, user_id: int):
    """
    1. Validate each room exists
    2. Check availability for date range
    3. Update room_status = HELD
    4. Set hold_expires_at = NOW() + 15 minutes
    5. Cache in Redis
    6. Return response
    """
    successfully_held = []
    failed = []
    
    for room_id in payload.room_ids:
        try:
            room = await fetch_room_by_id(db, room_id)
            if not room:
                failed.append({"room_id": room_id, "reason": "Room not found"})
                continue
            
            # Check if available
            if room.room_status != RoomStatus.AVAILABLE:
                failed.append({"room_id": room_id, "reason": f"Room {room.room_status}"})
                continue
            
            # Check booking conflicts
            has_booking = await check_booking_conflict(db, room_id, payload.check_in, payload.check_out)
            if has_booking:
                failed.append({"room_id": room_id, "reason": "Already booked for dates"})
                continue
            
            # Hold the room
            hold_until = datetime.utcnow() + timedelta(minutes=15)
            await update_room_by_id(db, room_id, {
                "room_status": RoomStatus.HELD,
                "freeze_reason": FreezeReason.SYSTEM_HOLD,
                "hold_expires_at": hold_until
            })
            
            successfully_held.append({
                "room_id": room_id,
                "room_no": room.room_no,
                "held_until": hold_until.isoformat() + "Z"
            })
        
        except Exception as e:
            failed.append({"room_id": room_id, "reason": str(e)})
    
    await db.commit()
    
    # Cache in Redis
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session_data = {
        "user_id": user_id,
        "room_ids": payload.room_ids,
        "held_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        "check_in": payload.check_in.isoformat(),
        "check_out": payload.check_out.isoformat(),
    }
    await set_cached(f"booking_session:{session_id}", session_data, ttl=900)
    
    return {
        "successfully_held": successfully_held,
        "failed": failed,
        "session_id": session_id,
        "message": "Rooms held successfully"
    }
```

#### ✅ IMPLEMENT: POST /room-management/rooms/unlock

```python
@router.post("/rooms/unlock", status_code=status.HTTP_200_OK)
async def unlock_rooms(
    payload: RoomUnlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Release held rooms"""
    result = await unlock_rooms_service(db, payload)
    return result
```

**Pydantic Model:**
```python
class RoomUnlockRequest(BaseModel):
    room_ids: List[int]
    reason: str = Field(..., pattern="^(payment_failed|session_expired|manual_release)$")
```

**Service Logic:**
```python
async def unlock_rooms_service(db: AsyncSession, payload: RoomUnlockRequest):
    successfully_released = []
    failed = []
    
    for room_id in payload.room_ids:
        try:
            room = await fetch_room_by_id(db, room_id)
            
            if room.room_status != RoomStatus.HELD:
                failed.append({"room_id": room_id, "reason": f"Room is {room.room_status}"})
                continue
            
            # Release the room
            await update_room_by_id(db, room_id, {
                "room_status": RoomStatus.AVAILABLE,
                "freeze_reason": FreezeReason.NONE,
                "hold_expires_at": None
            })
            
            successfully_released.append(room_id)
        
        except Exception as e:
            failed.append({"room_id": room_id, "reason": str(e)})
    
    await db.commit()
    
    return {
        "successfully_released": successfully_released,
        "failed": failed,
        "message": f"Released {len(successfully_released)} rooms"
    }
```

#### ✅ IMPLEMENT: GET /room-management/rooms/availability

```python
@router.get("/rooms/availability", response_model=List[Room])
async def get_available_rooms(
    check_in: date = Query(...),
    check_out: date = Query(...),
    room_type_id: Optional[int] = Query(None),
    adult_count: int = Query(1, ge=1),
    child_count: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Get rooms available for date range"""
    rooms = await check_availability_service(
        db, check_in, check_out, room_type_id, adult_count, child_count
    )
    return rooms
```

**Service Logic:**
```python
async def check_availability_service(
    db: AsyncSession, check_in, check_out, room_type_id, adult_count, child_count
):
    """
    Query logic:
    1. Find all rooms not deleted
    2. Filter by status (AVAILABLE or HELD with expired hold)
    3. Filter by occupancy
    4. Exclude booked date ranges
    5. Include amenities & images
    """
    
    query = select(Rooms).options(
        selectinload(Rooms.room_type),
        selectinload(Rooms.amenities).selectinload(RoomAmenityMap.amenity),
    ).where(
        Rooms.is_deleted == False,
        RoomTypes.is_deleted == False,
        or_(
            Rooms.room_status == RoomStatus.AVAILABLE,
            and_(
                Rooms.room_status == RoomStatus.HELD,
                Rooms.hold_expires_at < datetime.utcnow()
            )
        )
    )
    
    # Add date conflict check
    query = query.outerjoin(BookingRoomMap).outerjoin(Bookings).filter(
        or_(
            BookingRoomMap.room_id == None,
            and_(
                Bookings.status != 'Cancelled',
                Bookings.check_out <= check_in,
                Bookings.check_in >= check_out
            )
        )
    )
    
    # Filter by room type
    if room_type_id:
        query = query.where(Rooms.room_type_id == room_type_id)
    
    # Filter by occupancy
    query = query.where(
        RoomTypes.max_adult_count >= adult_count,
        RoomTypes.max_child_count >= child_count
    )
    
    result = await db.execute(query)
    return result.scalars().all()
```

#### ✅ IMPLEMENT: Scheduled Worker (Background Task)

**File:** `BACKEND/app/workers/release_room_holds_worker.py` (new file)

```python
import asyncio
from datetime import datetime
from sqlalchemy import select
from app.database.postgres_connection import AsyncSession, get_db
from app.models.sqlalchemy_schemas.rooms import Rooms, RoomStatus, FreezeReason
from app.crud.rooms import update_room_by_id
import logging

logger = logging.getLogger(__name__)

async def release_expired_holds(db: AsyncSession):
    """
    Called every 1 minute to release expired room holds
    
    Logic:
    1. Find all rooms where room_status=HELD AND hold_expires_at <= NOW()
    2. Set room_status=AVAILABLE, hold_expires_at=NULL
    3. Log action
    4. Notify customer (optional)
    """
    try:
        # Query expired holds
        query = select(Rooms).where(
            Rooms.room_status == RoomStatus.HELD,
            Rooms.hold_expires_at <= datetime.utcnow()
        )
        result = await db.execute(query)
        expired_rooms = result.scalars().all()
        
        if not expired_rooms:
            logger.debug("No expired holds found")
            return
        
        logger.info(f"Found {len(expired_rooms)} expired holds")
        
        # Release each room
        for room in expired_rooms:
            await update_room_by_id(db, room.room_id, {
                "room_status": RoomStatus.AVAILABLE,
                "freeze_reason": FreezeReason.NONE,
                "hold_expires_at": None
            })
            
            logger.info(f"Released hold on room {room.room_no}")
        
        await db.commit()
        logger.info(f"Successfully released {len(expired_rooms)} rooms")
    
    except Exception as e:
        logger.error(f"Error releasing holds: {str(e)}")
        await db.rollback()
        raise

# Schedule this to run every 1 minute
# In main.py or FastAPI startup:
# @app.on_event("startup")
# async def startup():
#     asyncio.create_task(schedule_worker())
#
# async def schedule_worker():
#     while True:
#         try:
#             async for db in get_db():
#                 await release_expired_holds(db)
#         except Exception as e:
#             logger.error(f"Worker error: {e}")
#         
#         await asyncio.sleep(60)  # Run every 60 seconds
```

#### ✅ UPDATE: API Response Models

Add to `BACKEND/app/schemas/pydantic_models/room.py`:

```python
class RoomWithAmenities(BaseModel):
    room_id: int
    room_no: str
    room_type_id: int
    room_type: RoomType
    amenities: List[Amenity]
    images: List[ImageResponse]
    room_status: RoomStatus
    nights: int
    total_price: float

class AvailabilityResponse(BaseModel):
    available_rooms: List[RoomWithAmenities]
    unavailable_count: int
    total_available: int
    filters_applied: dict
```

---

### Afternoon Session: Frontend Services (2-3 hours)

#### ✅ CREATE: TypeScript Models

**File:** `FRONTEND/src/app/features/rooms/models/room.model.ts`

```typescript
export interface RoomType {
  room_type_id: number;
  type_name: string;
  max_adult_count: number;
  max_child_count: number;
  price_per_night: number;
  square_ft: number;
  description?: string;
}

export interface Amenity {
  amenity_id: number;
  amenity_name: string;
}

export interface RoomImage {
  image_id: number;
  image_url: string;
  is_primary: boolean;
  caption?: string;
}

export interface Room {
  room_id: number;
  room_no: string;
  room_type_id: number;
  room_type: RoomType;
  amenities: Amenity[];
  images: RoomImage[];
  room_status: 'AVAILABLE' | 'BOOKED' | 'MAINTENANCE' | 'FROZEN' | 'HELD';
  freeze_reason?: string;
  hold_expires_at?: Date;
}

export interface AvailableRoom extends Room {
  nights: number;
  total_price: number;
}

export interface HoldResponse {
  successfully_held: {
    room_id: number;
    room_no: string;
    held_until: string;
  }[];
  failed: { room_id: number; reason: string }[];
  session_id: string;
  total_price: number;
  message: string;
}

export interface BookingSession {
  session_id: string;
  user_id: number;
  room_ids: number[];
  held_at: Date;
  expires_at: Date;
  check_in: Date;
  check_out: Date;
  nights: number;
  rooms: AvailableRoom[];
  total_price: number;
  payment_status: 'pending' | 'processing' | 'completed' | 'failed';
}
```

#### ✅ CREATE: Room Availability Service

**File:** `FRONTEND/src/app/features/rooms/services/room-availability.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AvailableRoom } from '../models/room.model';

@Injectable({ providedIn: 'root' })
export class RoomAvailabilityService {
  private baseUrl = `${environment.apiUrl}/room-management`;

  constructor(private http: HttpClient) {}

  /**
   * Get available rooms for date range
   */
  getAvailableRooms(
    checkIn: Date,
    checkOut: Date,
    adultCount: number = 1,
    childCount: number = 0,
    roomTypeId?: number
  ): Observable<AvailableRoom[]> {
    let params = new HttpParams()
      .set('check_in', checkIn.toISOString().split('T')[0])
      .set('check_out', checkOut.toISOString().split('T')[0])
      .set('adult_count', adultCount.toString())
      .set('child_count', childCount.toString());

    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId.toString());
    }

    return this.http.get<AvailableRoom[]>(
      `${this.baseUrl}/rooms/availability`,
      { params }
    );
  }
}
```

#### ✅ CREATE: Room Hold Service

**File:** `FRONTEND/src/app/features/rooms/services/room-hold.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { HoldResponse } from '../models/room.model';

@Injectable({ providedIn: 'root' })
export class RoomHoldService {
  private baseUrl = `${environment.apiUrl}/room-management`;
  private holdExpired$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  /**
   * Hold multiple rooms for 15 minutes
   */
  holdRooms(
    roomIds: number[],
    checkIn: Date,
    checkOut: Date
  ): Observable<HoldResponse> {
    const payload = {
      room_ids: roomIds,
      check_in: checkIn.toISOString().split('T')[0],
      check_out: checkOut.toISOString().split('T')[0]
    };

    return this.http.post<HoldResponse>(
      `${this.baseUrl}/rooms/hold`,
      payload
    );
  }

  /**
   * Release held rooms
   */
  releaseRooms(
    roomIds: number[],
    reason: 'payment_failed' | 'session_expired'
  ): Observable<any> {
    const payload = {
      room_ids: roomIds,
      reason
    };

    return this.http.post(
      `${this.baseUrl}/rooms/unlock`,
      payload
    );
  }

  /**
   * Observable for hold expiration
   */
  getHoldExpired(): Observable<void> {
    return this.holdExpired$.asObservable();
  }

  /**
   * Emit hold expiration
   */
  emitHoldExpired(): void {
    this.holdExpired$.next();
  }
}
```

#### ✅ CREATE: Timer Component

**File:** `FRONTEND/src/app/features/rooms/shared/availability-timer/availability-timer.component.ts`

```typescript
import { Component, Input, OnInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-availability-timer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="timer-container" [class.warning]="remainingSeconds < 300">
      <div class="timer-content">
        <span class="label">Session expires in:</span>
        <span class="time">{{ minutes }}:{{ seconds | padZero }}</span>
        <span class="status" *ngIf="remainingSeconds < 300" class="warning-text">
          ⚠️ Complete payment!
        </span>
      </div>
    </div>
  `,
  styles: [`
    .timer-container {
      padding: 15px;
      background: #f0f0f0;
      border-radius: 8px;
      margin: 15px 0;
      text-align: center;
    }

    .timer-container.warning {
      background: #fff3cd;
      border: 2px solid #ff9800;
    }

    .label {
      display: block;
      font-size: 14px;
      color: #666;
      margin-bottom: 5px;
    }

    .time {
      display: block;
      font-size: 32px;
      font-weight: bold;
      color: #333;
      font-family: 'Courier New', monospace;
    }

    .warning-text {
      display: block;
      color: #ff6b6b;
      margin-top: 10px;
      font-weight: bold;
    }
  `]
})
export class AvailabilityTimerComponent implements OnInit, OnDestroy {
  @Input() expiresAt: Date;
  @Output() sessionExpired = new EventEmitter<void>();

  remainingSeconds = 900; // 15 minutes
  minutes = 15;
  seconds = 0;
  private subscription: Subscription;

  ngOnInit() {
    this.startCountdown();
  }

  private startCountdown() {
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
    this.subscription?.unsubscribe();
    this.sessionExpired.emit();
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
  }
}

// Pipe for padding zeros
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'padZero',
  standalone: true
})
export class PadZeroPipe implements PipeTransform {
  transform(value: number): string {
    return value.toString().padStart(2, '0');
  }
}
```

---

### Evening Session: Frontend Components (2-3 hours)

#### ✅ CREATE: Room Search Component

**File:** `FRONTEND/src/app/features/rooms/customer/room-search/room-search.component.ts`

```typescript
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RoomAvailabilityService } from '../../services/room-availability.service';
import { AvailableRoom } from '../../models/room.model';

@Component({
  selector: 'app-room-search',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="search-container">
      <h2>Search Rooms</h2>
      
      <form [formGroup]="searchForm" (ngSubmit)="onSearch()">
        <div class="form-group">
          <label>Check-in Date</label>
          <input type="date" formControlName="checkIn" required />
        </div>

        <div class="form-group">
          <label>Check-out Date</label>
          <input type="date" formControlName="checkOut" required />
        </div>

        <div class="form-group">
          <label>Adults</label>
          <input type="number" formControlName="adults" min="1" required />
        </div>

        <div class="form-group">
          <label>Children</label>
          <input type="number" formControlName="children" min="0" />
        </div>

        <button type="submit" [disabled]="loading">
          {{ loading ? 'Searching...' : 'Search' }}
        </button>
      </form>

      <div *ngIf="availableRooms.length" class="results">
        <h3>{{ availableRooms.length }} Rooms Available</h3>
        <!-- Room list component here -->
      </div>

      <div *ngIf="error" class="error">
        {{ error }}
      </div>
    </div>
  `
})
export class RoomSearchComponent {
  searchForm: FormGroup;
  availableRooms: AvailableRoom[] = [];
  loading = false;
  error: string;

  constructor(
    private fb: FormBuilder,
    private roomService: RoomAvailabilityService
  ) {
    this.searchForm = this.fb.group({
      checkIn: ['', Validators.required],
      checkOut: ['', Validators.required],
      adults: [1, Validators.required],
      children: [0]
    });
  }

  onSearch() {
    if (!this.searchForm.valid) return;

    this.loading = true;
    this.error = null;

    const { checkIn, checkOut, adults, children } = this.searchForm.value;

    this.roomService.getAvailableRooms(
      new Date(checkIn),
      new Date(checkOut),
      adults,
      children
    ).subscribe({
      next: (rooms) => {
        this.availableRooms = rooms;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to search rooms: ' + err.message;
        this.loading = false;
      }
    });
  }
}
```

---

## 📝 TESTING CHECKLIST

### Unit Tests (Backend)

- [ ] Test hold_rooms_service with valid rooms
- [ ] Test hold_rooms_service with already-booked room
- [ ] Test hold_rooms_service with invalid date range
- [ ] Test unlock_rooms_service with HELD room
- [ ] Test unlock_rooms_service with AVAILABLE room (should fail)
- [ ] Test check_availability_service with various date ranges
- [ ] Test availability query excludes HELD rooms until expiry
- [ ] Test Redis cache stores session data correctly

### Integration Tests (Backend)

- [ ] Hold room → check database status is HELD
- [ ] Hold room → check Redis has session
- [ ] Unlock room → check database status is AVAILABLE
- [ ] Unlock room → check Redis clears session
- [ ] Worker task → release expired holds after 15 min

### E2E Tests (Full Flow)

- [ ] Search available rooms for 2-day range
- [ ] Select multiple rooms
- [ ] Hold rooms (status changes to HELD)
- [ ] Timer starts and counts down
- [ ] Payment success → rooms become BOOKED
- [ ] Payment failure → rooms released to AVAILABLE
- [ ] Wait 15 mins → worker releases rooms automatically

### Frontend Tests

- [ ] Search form validation
- [ ] Timer counts down from 15:00 to 0:00
- [ ] Timer styling changes when < 5 minutes
- [ ] Room cards display correctly
- [ ] Selection tracking works
- [ ] Error messages display properly

---

## 🔧 DATABASE CHECKLIST

- [ ] Verify `hold_expires_at` column exists in `rooms` table
- [ ] Verify indexes on `room_status`, `hold_expires_at`
- [ ] Verify foreign keys on `booking_room_map`
- [ ] Run migrations if any schema changes needed
- [ ] Test database constraints
- [ ] Backup database before schema changes

---

## 📦 DEPENDENCIES TO ADD

### Backend
```
# Already in requirements.txt likely:
fastapi
sqlalchemy
pydantic
asyncio
redis  # if not present
python-dateutil
```

### Frontend
```typescript
// Already in package.json likely:
@angular/common
@angular/core
@angular/forms
@angular/http
rxjs
```

---

## 🚨 CRITICAL REMINDERS

1. **Always** set `hold_expires_at` when holding rooms
2. **Always** check expired holds in availability query
3. **Always** release rooms on payment failure immediately
4. **Always** run worker task every 1 minute (not 5 or 10)
5. **Always** validate dates before holding
6. **Always** handle timezone issues (use UTC everywhere)
7. **Always** cache in Redis with 15-min TTL
8. **Always** test 15-minute timer manually
9. **Always** clear cache on successful booking
10. **Always** log all hold/release actions for debugging

---

## ✅ END OF DAY COMPLETION CRITERIA

```
✅ Backend APIs working in Postman:
   └─ POST /rooms/hold
   └─ POST /rooms/unlock
   └─ GET /rooms/availability

✅ Timer component displays correctly

✅ Room search shows available rooms

✅ Multi-room hold works

✅ Payment success → booking created

✅ Payment failure → rooms released

✅ 15-minute timeout → worker releases rooms

✅ Database state correct at each step

✅ All edge cases handled

✅ No console errors

✅ Ready for booking module integration
```

---

## 📞 QUICK LINKS & REFERENCES

- Existing Room Routes: `BACKEND/app/routes/rooms.py`
- Existing Room Services: `BACKEND/app/services/rooms.py`
- Existing Schemas: `BACKEND/app/schemas/pydantic_models/room.py`
- Room Models: `BACKEND/app/models/sqlalchemy_schemas/rooms.py`
- Booking Models: `BACKEND/app/models/sqlalchemy_schemas/bookings.py`
- Cache Utility: `BACKEND/app/core/redis_manager.py`
- Frontend Service Template: Already exists at `FRONTEND/src/app/core/services/rooms/`

