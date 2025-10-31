# Room Management — API Reference

This file documents the HTTP APIs implemented under `app/routes/room_management`.

Summary of routers and endpoints:

## Room Types
Base path: `/api/room-types`

- POST `/` — Create a room type
  - Auth: requires non-basic user (`ensure_not_basic_user`) — used for admin/manager actions.
  # Room Management — API Reference

  This file documents the HTTP APIs implemented under `app/routes/room_management`.

  Summary of routers and endpoints:

  ## Room Types
  Base path: `/api/room-types`

  - POST `/` — Create a room type
    - Auth: requires non-basic user (`ensure_not_basic_user`) — used for admin/manager actions.
    - Request body: `RoomTypeCreate` (JSON)
    - Response: `RoomTypeResponse` (201 Created)

  - GET `/` — List room types
    - Query: `include_deleted: bool` (optional)
    - Response: list[`RoomTypeResponse`]

  - GET `/{room_type_id}` — Get a single room type
    - Path param: `room_type_id: int`
    - Response: `RoomTypeResponse`

  - PUT `/{room_type_id}` — Update a room type
    - Auth: `ensure_not_basic_user`
    - Request body: `RoomTypeCreate` (JSON)
    - Response: `RoomTypeResponse`

  - DELETE `/{room_type_id}` — Soft-delete a room type
    - Auth: `ensure_not_basic_user`

  ## Full API List (routes discovered in app/routes)

  ### Auth
  Base path: /auth

  - POST /signup
  - POST /otp/request
  - POST /otp/verify
  - POST /change-password
  - POST /login
  - POST /refresh
  - POST /logout
  - POST /admin/register

  ### Roles
  Base path: /roles

  - POST /
  - GET /

  ### Permissions
  Base path: /permissions

  - POST /                (create permissions)
  - POST /assign          (assign permissions to role)
  - GET /by-role/{role_id}
  - GET /by-resources
  - GET /{permission_id}/roles

  ### Room Management — Room Types
  Base path: /api/room-types

  - POST /
  - GET /
  - GET /{room_type_id}
  - PUT /{room_type_id}
  - DELETE /{room_type_id}

  ### Room Management — Rooms
  Base path: /api/rooms

  - POST /
  - GET /
  - GET /{room_id}
  - PUT /{room_id}
  - PATCH /{room_id}/status
  - DELETE /{room_id}

  ### Room Management — Amenities
  Base path: /api/amenities

  - POST /
  - GET /
  - GET /{amenity_id}
  - DELETE /{amenity_id}

  ### Room Management — Room–Amenity Mapping
  Base path: /api/room-amenities

  - POST /
  - GET /room/{room_id}
  - DELETE /

  ### Room Management — Room Images
  Base path: /api/rooms/{room_id}/images

  - POST /    (multipart/form-data: image file, caption, is_primary)
  - GET /

  ---

  This file lists the HTTP endpoints found under `app/routes`. It intentionally contains only endpoints and their paths.
  ---