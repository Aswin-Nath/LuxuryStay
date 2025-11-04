# API Reference

This document lists the HTTP APIs implemented in `app/routes` (grouped by feature). For each router I show the base path and the endpoints defined in the repository as of this commit. Where the code enforces authentication or permission checks I note that briefly.

## Auth
Base path: `/auth`

- POST `/signup` — Create user (request: `UserCreate`, response: `UserResponse`)  (201)
- POST `/otp/request` — Request OTP for verification/password reset (202)
- POST `/otp/verify` — Verify OTP (optionally reset password)
- POST `/change-password` — Change password (authenticated)
- POST `/login` — OAuth2 login (form-data) — returns tokens (`TokenResponse`)
- POST `/refresh` — Rotate tokens using refresh token (`TokenResponse`)
- POST `/logout` — Logout (blacklist/revoke token)
- POST `/admin/register` — Create admin user (permission-protected; requires Admin_Creation/WRITE)

## Roles
Base path: `/roles`

- POST `/` — Create a role (request: `RoleCreate`, response: `RoleResponse`)
- GET `/` — List roles (response: list[`RoleResponse`])

## Permissions
Base path: `/permissions`

- POST `/` — Create permissions (accepts list of `PermissionCreate`, response: list[`PermissionResponse`])
- POST `/assign` — Assign permissions to role (request: `RolePermissionAssign`, response: `RolePermissionResponse`)
- GET `/by-role/{role_id}` — Get permissions by role id
- GET `/by-resources` — Get permissions by multiple resources (query param list)
- GET `/{permission_id}/roles` — Get roles assigned to a permission

## Room Management (grouped)
This package bundles room types, rooms, amenities, room–amenity mapping and room images. Common prefix usage is shown per sub-router below.

### Room Types
Base path: `/api/room-types`

- POST `/` — Create a room type (request: `RoomTypeCreate`, response: `RoomTypeResponse`) (201)
  - Permission: requires ROOM_MANAGEMENT.WRITE (permission dependency)
- GET `/` — List room types (query: `include_deleted: bool`) (response: list[`RoomTypeResponse`])
- GET `/{room_type_id}` — Get a single room type
- PUT `/{room_type_id}` — Update a room type (permission: ROOM_MANAGEMENT.WRITE)
- DELETE `/{room_type_id}` — Soft-delete a room type (permission: ROOM_MANAGEMENT.WRITE)

### Rooms
Base path: `/api/rooms`

- POST `/` — Create a room (request: `RoomCreate`, response: `RoomResponse`) (201)
  - Permission: requires both BOOKING.WRITE and ROOM_MANAGEMENT.WRITE
- GET `/` — List rooms (query filters: `room_type_id`, `status_filter`, `is_freezed`)
- GET `/{room_id}` — Get room details (response: `RoomResponse`)
- PUT `/{room_id}` — Update a room (permission: BOOKING.WRITE & ROOM_MANAGEMENT.WRITE)
- PATCH `/{room_id}/status` — Change room status (permission: BOOKING.WRITE & ROOM_MANAGEMENT.WRITE)
- DELETE `/{room_id}` — Delete a room (permission: BOOKING.WRITE & ROOM_MANAGEMENT.WRITE)

### Amenities
Base path: `/api/amenities`

- POST `/` — Create an amenity (request: `AmenityCreate`, response: `AmenityResponse`) (201)
  - Permission: ROOM_MANAGEMENT.WRITE
- GET `/` — List amenities
- GET `/{amenity_id}` — Get amenity
- DELETE `/{amenity_id}` — Delete amenity (permission: ROOM_MANAGEMENT.WRITE)

### Room–Amenity Mapping
Base path: `/api/room-amenities`

- POST `/` — Map amenity to room (request: `RoomAmenityMapCreate`, response: `RoomAmenityMapResponse`) (201)
  - Permission: ROOM_MANAGEMENT.WRITE
- GET `/room/{room_id}` — Get amenities for a room
- DELETE `/` — Unmap amenity (query: room_id, amenity_id) (permission: ROOM_MANAGEMENT.WRITE)

### Room Images
Base path: `/api/rooms/{room_id}/images`

- POST `/` — Upload image for room (multipart/form-data: file, caption, is_primary) (201)
  - Permission: ROOM_MANAGEMENT.WRITE (uploader must be authenticated)
- GET `/` — List images for room (response: list[`ImageResponse`])
- DELETE `/{image_id}` — Hard-delete image (204) — requester must be uploader or have ROOM_MANAGEMENT.WRITE

## Offers
Base path: `/api/offers`

- POST `/` — Create offer (request: `OfferCreate`, response: `OfferResponse`) (201)
  - Permission: OFFER_MANAGEMENT.WRITE
- GET `/{offer_id}` — Get offer
- GET `/` — List offers (query: limit/offset)
- PUT `/{offer_id}` — Edit offer (permission: OFFER_MANAGEMENT.WRITE)
- DELETE `/{offer_id}` — Soft-delete offer (permission: OFFER_MANAGEMENT.WRITE)

## Bookings
Base path: `/api/bookings`

- POST `/` — Create booking (request: `BookingCreate`, response: `BookingResponse`) (201)
  - Permission: BOOKING.WRITE (enforced)
- GET `/` — List bookings (limit/offset)
- GET `/query` — Query bookings (filters: user_id, status)
- GET `/{booking_id}` — Get booking details

## Reviews
Base path: `/api/reviews`

- POST `/` — Create review (request: `ReviewCreate`, response: `ReviewResponse`) (201) — authenticated
- GET `/` — List or get review(s). Query params: `review_id`, `booking_id`, `room_id`, `user_id` — returns single or list depending on params
- PUT `/{review_id}/respond` — Admin respond to review (request: `AdminResponseCreate`) — requires non-basic/admin
- PUT `/{review_id}` — Update review (authenticated reviewer)

## Notifications
Base path: `/api/notifications`

- POST `/` — Create notification (request: `NotificationCreate`, response: `NotificationResponse`) (201) — authenticated
- GET `/` — List notifications (query: include_read/include_deleted/limit/offset) — authenticated

## Refunds
Base path: `/api`

- POST `/bookings/{booking_id}/cancel` — Cancel booking and create refund (request: `RefundCreate`, response: `RefundResponse`) (201) — authenticated
- PUT `/refunds/{refund_id}/transaction` — Update refund transaction (admin-only / ensure_not_basic_user)

## Wishlist
Base path: `/api/wishlist`

- POST `/` — Add to wishlist (request: `WishlistCreate`, response: `WishlistResponse`) (201) — authenticated
- GET `/` — List wishlist for current user — authenticated
- GET `/item` — Get single wishlist item by `room_type_id` or `offer_id` — authenticated
- DELETE `/{wishlist_id}` — Remove wishlist item (204) — authenticated

## Issues (Issue Management)
Customer base path: `/api/issues`

- POST `/` — Create issue (multipart/form-data: booking_id, title, description, optional images) (201) — authenticated
- GET `/` — List current user's issues (limit/offset)
- GET `/{issue_id}` — Get a user's issue (403 if not owner)
- PUT `/{issue_id}` — Update a user's issue (multipart/form-data; images optional)
- POST `/{issue_id}/chat` — Post chat/message to an issue (201)
- GET `/{issue_id}/chat` — List chats for an issue

## Booking Edits

Base path: `/api/booking-edits`

- POST `/` — Create a booking edit request (request: `BookingEditCreate`, response: `BookingEditResponse`) (201) — authenticated
- GET `/active` — Get the current active booking-edit for the user (response: `BookingEditResponse | None`)
- GET `/{booking_id}` — List booking-edit requests for a booking (response: list[`BookingEditResponse`])
- POST `/{edit_id}/review` — Submit reviewer feedback for an edit request (authenticated reviewer)
- POST `/{edit_id}/decision` — Submit decision on a booking edit (approve/deny) — permission-protected

Admin base path: `/api/admin/issues`

- GET `/` — List issues (admin permission: ISSUE_RESOLUTION.WRITE)
- GET `/{issue_id}` — Get issue
- PUT `/{issue_id}` — Admin update issue (status updates, mark resolved)
- POST `/{issue_id}/chat` — Admin post chat to an issue (201)
- GET `/{issue_id}/chat` — List chats for issue

---

Notes
- The API surface above is collected from the route definitions under `app/routes` and the routers included in `app/main.py`.
- Many endpoints require authentication; several require permission checks (examples: ROOM_MANAGEMENT.WRITE, OFFER_MANAGEMENT.WRITE, BOOKING.WRITE, ISSUE_RESOLUTION.WRITE, Admin_Creation.WRITE). Refer to the route function docstrings and the dependencies in `app/dependencies/authentication.py` for exact enforcement.

If you want I can also generate a machine-readable OpenAPI-like excerpt (YAML/JSON) or a small Markdown table per router; tell me which format you prefer.
