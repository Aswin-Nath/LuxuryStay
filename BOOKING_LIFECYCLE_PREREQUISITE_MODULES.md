# 📋 Booking Lifecycle - Prerequisite Modules

## 🎯 Your Goal
You want to implement the **8 Booking Lifecycle Modules**:
1. Admin Bookings
2. Admin Individual Bookings
3. Customer Maintaining the Lifecycle of the Booking
4. Customer Cancel (Amount calculation based on room prices)
5. Customer Pre-Edit
6. Customer Post-Edit (Only keep last BookingRoomMap)
7. Admin Transfer Room (Renovation handling per room)
8. Admin Cancel (Emergency - Full Refunds)

---

## ✅ PREREQUISITE MODULES TO COMPLETE FIRST

### **Group 1: CRITICAL Dependencies** (Do These FIRST)
These must be completed before any lifecycle work:

#### 1. **🏢 Room Lifecycle Management** (Based on Booking Status)
**Why**: Each booking affects room availability and status
**Status**: 
- Backend: ✅ Mostly Done (routes/v2_booking.py, CRUD operations exist)
- Angular: ❌ Not Started
**What's Needed**:
- Room status state machine: `AVAILABLE` → `HELD` → `BOOKED` → `CHECKED_IN` → `CHECKED_OUT`
- Auto-transition rooms to `AVAILABLE` when booking is cancelled/completed
- Mark rooms `IN_MAINTENANCE` for renovations
- Backend logic to update room status based on booking lifecycle events
- Angular component to visualize room availability calendar

**Complexity**: ⭐⭐⭐ Medium-High

---

#### 2. **💰 Payment Gateway Integration** (Refunds & Transactions)
**Why**: Cancellations and refunds require payment processing
**Status**:
- Backend: ✅ Exists (routes/payments.py, models for payments)
- Angular: ⏳ Partial (Payment form exists in booking component)
**What's Needed**:
- Payment status tracking: `PENDING` → `COMPLETED` → `REFUNDED` → `FAILED`
- Refund calculation engine (percentage-based on cancellation time)
- Multiple payment method support: Card, UPI, Net Banking
- Transaction history & receipts
- Payment verification webhook handling (Stripe/Razorpay)

**Complexity**: ⭐⭐⭐⭐ High

---

#### 3. **📊 Booking Status State Machine**
**Why**: Every lifecycle action depends on current booking status
**Status**:
- Backend: ⏳ Partial (status field exists but transitions not enforced)
- Angular: ⏳ Partial (basic status display exists)
**What's Needed**:
- Define all valid status transitions:
  ```
  PENDING → CONFIRMED → CHECKED_IN → CHECKED_OUT
  PENDING → CANCELLED (from either admin or customer)
  CONFIRMED → CANCELLED (with refund calculation)
  ```
- Backend validator to prevent invalid transitions
- Audit trail for status changes (who changed it, when, why)
- Angular state display with transition buttons (contextual actions)

**Complexity**: ⭐⭐⭐ Medium

---

### **Group 2: IMPORTANT Modules** (Do After Group 1)
These are tightly coupled but can be done in parallel:

#### 4. **⭐ Reviews Module**
**Why**: Customer feedback system needed for post-checkout bookings
**Status**:
- Backend: ✅ Complete (routes/reviews.py with full CRUD)
- Angular: ❌ Not Started
**What's Needed**:
- Review form component (rating 1-5, comments, images)
- Review submission after checkout
- Admin response to reviews
- Review listing/filtering
- Image upload for reviews

**Complexity**: ⭐⭐ Low-Medium

---

#### 5. **🔧 Issues/Complaints Module**
**Why**: Customers need to report problems during/after booking
**Status**:
- Backend: ✅ Complete (routes/issues.py with chat system)
- Angular: ❌ Not Started
**What's Needed**:
- Issue report form
- Issue status tracking: `OPEN` → `IN_PROGRESS` → `RESOLVED` → `CLOSED`
- Admin-Customer chat interface for issue resolution
- Issue priority management
- Issue history & resolution time tracking

**Complexity**: ⭐⭐⭐ Medium

---

#### 6. **❤️ Wishlist Module**
**Why**: Customer convenience feature for future bookings
**Status**:
- Backend: ✅ Complete (routes/wishlist.py)
- Angular: ❌ Not Started
**What's Needed**:
- Add/remove from wishlist button on rooms
- Wishlist page with saved rooms
- Price tracking on wishlisted rooms
- Wishlist notifications (price drops, availability)

**Complexity**: ⭐⭐ Low

---

#### 7. **💵 Refunds Module**
**Why**: CRITICAL for cancellations and emergency admin cancels
**Status**:
- Backend: ✅ Complete (routes/refund.py with transaction tracking)
- Angular: ❌ Not Started
**What's Needed**:
- Refund calculation engine:
  - Full refund if cancelled >X days before check-in
  - Partial refund (50%) if cancelled X-Y days before check-in
  - No refund if cancelled <X days before check-in
  - Emergency admin cancel = Full refund regardless of timing
- Refund status page (Admin & Customer views)
- Payment gateway integration for actual refund processing
- Refund receipt/confirmation

**Complexity**: ⭐⭐⭐⭐ High (Logic & Integration)

---

### **Group 3: SUPPORTING Modules** (Nice-to-Have, Can Parallel)
These enhance but aren't blockers:

#### 8. **🔔 Notifications Module**
**Why**: Keep users updated on booking changes
**Status**:
- Backend: ✅ Complete (routes/notifications.py)
- Angular: ❌ Not Started
**What's Needed**:
- Email/SMS notifications for:
  - Booking confirmation
  - Booking reminders (1 day before)
  - Check-in/Check-out notifications
  - Cancellation confirmation
  - Refund status updates
- In-app notification center
- Notification preferences/settings

**Complexity**: ⭐⭐ Low (if using services like SendGrid/Twilio)

---

#### 9. **📱 Booking Confirmation & Receipt**
**Why**: Customer needs booking details & proof
**Status**:
- Backend: ⏳ Partial (Invoice/Receipt generation needed)
- Angular: ✅ Partial (booking-details component exists)
**What's Needed**:
- Generate PDF receipt/invoice
- Receipt email delivery
- Download receipt from booking details page
- QR code for check-in

**Complexity**: ⭐⭐ Low-Medium

---

#### 10. **📈 Audit & Logging**
**Why**: Track all booking lifecycle changes for compliance
**Status**:
- Backend: ⏳ Partial (audit_service.py exists but needs enhancement)
- Angular: ❌ Not Started
**What's Needed**:
- Log all booking state changes
- Log all refund transactions
- Admin audit trail view
- Compliance reports (GDPR, financial audits)

**Complexity**: ⭐⭐ Low

---

## 🚀 RECOMMENDED IMPLEMENTATION ORDER

```
PHASE 1 (Blocking - Must Do First):
├─ 1. Booking Status State Machine (Backend)
├─ 2. Room Lifecycle Management (Backend + Angular)
├─ 3. Payment Gateway Integration (Backend focus)
└─ 4. Refunds Module (Backend focus)

PHASE 2 (Immediate - Before Lifecycle Work):
├─ 5. Reviews Module (Angular)
├─ 6. Issues Module (Angular)
├─ 7. Wishlist Module (Angular)
└─ 8. Notifications Module (Angular)

PHASE 3 (Supporting - During Lifecycle Work):
├─ 9. Booking Confirmation & Receipt (Both)
└─ 10. Audit & Logging (Both)

PHASE 4 (THEN - Your Main 8 Lifecycle Modules):
├─ Admin Bookings
├─ Admin Individual Bookings
├─ Customer Lifecycle
├─ Customer Cancel
├─ Customer Pre-Edit
├─ Customer Post-Edit
├─ Admin Transfer Room
└─ Admin Emergency Cancel
```

---

## 📊 Dependency Graph

```
┌─────────────────────────────────────────────────────┐
│  Booking Lifecycle Modules (Your Goal - Phase 4)    │
│  1. Admin Bookings                                  │
│  2. Admin Individual Bookings                       │
│  3. Customer Maintaining Lifecycle                  │
│  4. Customer Cancel                                 │
│  5. Customer Pre-Edit                               │
│  6. Customer Post-Edit                              │
│  7. Admin Transfer Room                             │
│  8. Admin Emergency Cancel                          │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────┴────────────────┐
         ▼                            ▼
    ┌─────────────┐            ┌──────────────┐
    │  REFUNDS    │            │ NOTIFICATIONS│
    │  (Critical) │            │  (Support)   │
    └────┬────────┘            └──────────────┘
         │
    ┌────┴────────────────────────────┐
    ▼                                  ▼
┌─────────────────────┐    ┌──────────────────────┐
│ Room Lifecycle Mgmt │    │ Booking Status State │
│ (CRITICAL)          │    │ Machine (CRITICAL)   │
│ - Auto transitions  │    │ - Enforce rules      │
│ - Availability      │    │ - Audit changes      │
└─────────────────────┘    └──────────────────────┘
    │                            │
    │                            │
    └────────────┬───────────────┘
                 ▼
    ┌──────────────────────┐
    │ Payment Integration  │
    │ (HIGH Priority)      │
    │ - Process payments   │
    │ - Calculate refunds  │
    └──────────────────────┘
```

---

## ⚡ Quick Start Checklist for Phase 1

- [ ] **Booking Status State Machine**
  - [ ] Backend: Create status transition validator
  - [ ] Backend: Prevent invalid transitions (middleware/service)
  - [ ] Backend: Audit log status changes
  - [ ] DB: Add status change audit table

- [ ] **Room Lifecycle Management**
  - [ ] Backend: Create room status event handler
  - [ ] Backend: Auto-update room status based on booking events
  - [ ] Backend: Handle room maintenance/renovation locks
  - [ ] Angular: Room availability calendar component
  - [ ] Angular: Room status visualization

- [ ] **Payment Gateway** (Setup)
  - [ ] Backend: Complete payment model relationships
  - [ ] Backend: Add transaction status tracking
  - [ ] Backend: Refund calculation logic
  - [ ] Integrate Stripe/Razorpay (or your preferred gateway)

- [ ] **Refunds Module**
  - [ ] Backend: Refund policy engine (timing-based percentages)
  - [ ] Backend: Calculate refund amounts per room
  - [ ] Backend: Refund transaction processing
  - [ ] Angular: Refund status page

---

## 💡 Key Insights

1. **Refunds are tied to Time-Based Rules**: 
   - Customer cancels 30 days before = Full refund
   - Customer cancels 15 days before = 50% refund
   - Customer cancels <7 days = No refund
   - Admin emergency cancel = Always full refund

2. **Room Status Management is Automatic**:
   - When booking → CONFIRMED, rooms become BOOKED
   - When booking → CANCELLED, rooms become AVAILABLE
   - When booking → CHECKED_OUT, rooms become AVAILABLE
   - When admin transfers room, previous room becomes AVAILABLE, new room becomes BOOKED

3. **Payment & Refund are Coupled**:
   - Every cancellation triggers a refund calculation
   - Every refund needs payment gateway interaction
   - Refund status must sync back to booking status

4. **State Machines Prevent Bugs**:
   - Can't cancel an already-cancelled booking
   - Can't refund a never-paid booking
   - Can't check-in past checkout time
   - Can't transfer room if no renovation reason

---

## 🎓 Suggested Module Dependencies Order (Timeline)

**Week 1**: 
- Booking Status State Machine (Backend)
- Room Lifecycle Management (Backend + Angular)

**Week 2**:
- Payment Integration
- Refunds Module (Backend)

**Week 3**:
- Reviews Module (Angular)
- Issues Module (Angular)

**Week 4**:
- Wishlist Module (Angular)
- Notifications (Backend connection)

**Week 5-8**:
- Your 8 Lifecycle Modules

---

## 🤔 Questions to Answer Before Starting

1. **Refund Policy**: What % refund for different cancellation windows?
2. **Payment Methods**: Which gateways? (Stripe, Razorpay, etc.)
3. **Email Notifications**: Who sends? (SendGrid, AWS SES, etc.)
4. **Admin Permissions**: Can only managers cancel? Or any admin?
5. **Room Transfer**: Can customer request, or admin-only?
