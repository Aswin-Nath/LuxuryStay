# Copilot / AI Agent Instructions for HotelBookingSystem

This file gives concise, actionable context to make an AI coding assistant productive in this repository.

- Project type: FastAPI backend (Python). App entry: `app/main.py` (routers are registered there).
- Major components:
  - `app/routes/` — feature-based routers (e.g. `room_management`, `auth`, `offers`, `booking`, `issue_management`). Each feature folder exposes a FastAPI router that `app/main.py` includes.
  - `app/services/` — business-logic/services layer. Routes should call service functions; avoid heavy logic in routers.
  - `app/models/pydantic_models/` — request/response Pydantic models used by endpoints.
  - `app/models/sqlalchemy_schemas/` — SQLAlchemy table models for Postgres-backed entities.
  - `app/models/motor_schemas/` — MongoDB (motor) schemas used for collections (logs, backups, etc.).
  - `database/` — DB helpers: `postgres_connection.py`, `mongo_connnection.py`, and `create_tables.py` for initial SQL setup.
  - `app/core/` — cross-cutting concerns: `logger.py`, `security.py`, `exceptions.py`, `config.py` (config values live here; `config.py` may be empty or environment-driven).
  - `app/middlewares/` — custom middleware (error handler, CORS, auth, rate limiter).
  - `dependencies/` — dependency-injection helpers (e.g. authentication dependency used by routes).

Key patterns and conventions (do not assume defaults elsewhere):
- Router inclusion: New feature routers must be imported and included in `app/main.py` with `app.include_router(...)`.
- Separation-of-concerns: routes -> services -> database. Look for corresponding `service` files when editing endpoints.
- Dual persistence: project uses both Postgres (SQLAlchemy) and Mongo (motor). Use the appropriate folder (`sqlalchemy_schemas` vs `motor_schemas`) depending on the model.
- Pydantic models are the canonical API contract. Example: `app/models/pydantic_models/reviews.py` models request/response shapes used by review endpoints.
- Error handling: custom exceptions live in `app/core/exceptions.py`. The middleware `app/middlewares/error_handler.py` maps those to HTTP responses — raise domain exceptions rather than HTTPExceptions where appropriate.
- Authentication & authorization: look at `dependencies/authentication.py` and `app/core/security.py`. Routes use dependencies like `ensure_not_basic_user` to restrict admin/manager actions.
- File uploads: room images endpoints use multipart/form-data; see `app/routes/room_management` and `app/services/image_service.py` for handling and storage patterns.

Developer workflows (how to run & test locally):
- Create/activate virtualenv (Windows CMD):

  Scripts\activate.bat

- Run app locally (common FastAPI / uvicorn pattern):

  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  (Add `--env-file .env` if you maintain env file — check `app/core/config.py` and `database/*` for env usage.)

- DB setup:
  - Postgres tables: `python database/create_tables.py` (inspect the script — it runs SQLAlchemy metadata.create_all).
  - Mongo: `database/mongo_connnection.py` contains the connection helper.

- Tests: there are `tests/unit/` and `tests/integration/`. The repo does not include a pinned test runner file in `requirements.txt` — use `pytest` if present in your environment.

Integration & external dependencies:
- Postgres — SQLAlchemy used for relational models under `app/models/sqlalchemy_schemas` and `database/postgres_connection.py`.
- MongoDB — motor/mongo used for NoSQL collections in `app/models/motor_schemas` and `database/mongo_connnection.py`.
- Third-party services: image storage and other external integrations are usually wrapped by `app/services/*` — prefer to call those wrappers instead of calling SDKs directly from routes.

Where to look for examples when editing:
- Adding a new endpoint: follow pattern in `app/routes/room_management/*` and `app/routes/booking/customer.py` — route -> pydantic model -> service call -> service uses DB helper.
- Authorization example: `app/routes/roles/roles.py` and `app/routes/auth/auth.py` show how dependencies and tokens are used.
- DB migration/initialization: `database/create_tables.py` shows how tables are created programmatically.

Quick debugging tips:
- Check logs from `app/core/logger.py` and ensure `config` (env vars) are set for DB URIs.
- If a route raises an application-specific error, the middleware in `app/middlewares/error_handler.py` will convert it to a client-friendly response.

Editing rules for AI assistants (concise):
- Preserve public API shapes defined in `pydantic_models` unless explicitly asked to change them — those are used across clients and tests.
- When adding data fields, update both the Pydantic model and the SQLAlchemy/Mongo schema that persists it.
- Prefer using existing `service` functions; add new service functions under `app/services` rather than placing logic in routers.
- When modifying database code, run/modify `database/create_tables.py` or appropriate migration scripts under `database/migrations`.
- For changes touching CI, tests, or dependencies, call out required `requirements.txt` updates and add minimal tests under `tests/unit`.

If anything here is unclear or you'd like more detail (example: environment variables expected by DB connectors or preferred testing command), tell me which area to expand and I will update this file.