from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio

from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from app.routes.roles_and_permissions import roles_and_permissions_router
from app.routes.authentication import auth_router
from app.routes.rooms import router as room_management_router
from app.routes.booking import router as booking_customer_router
from app.routes.wishlist import router as wishlist_router
from app.routes.notifications import router as notifications_router
from app.routes.issues import router as issue_router
from app.routes.reviews import router as reviews_router
from app.routes.refund import router as refunds_router
from app.routes.profile import router as profile_router
from app.routes.logs import router as logs_router
from app.routes.backups import router as backups_router
from app.routes.restores import router as restores_router
from app.routes.reports import router as reports_router
from app.routes.content import router as content_router
from app.routes.payments import router as payment_router
from app.routes.users import users_router
from app.routes.v2_booking import router as v2_booking_router
from app.routes.offers import router as offers_router
from app.routes.images import router as images_router
from app.workers.release_room_holds_worker import run_hold_release_scheduler
from app.workers.booking_lifecycle_hourly_worker import run_hourly_booking_lifecycle_scheduler
from app.workers.room_lifecycle_daily_worker import run_daily_checkout_scheduler_at_1159pm
from app.workers.offers_expiry_worker import run_offer_expiry_scheduler_at_1159pm
import os
import logging
from contextlib import asynccontextmanager
_logger = logging.getLogger(__name__)

# ---- lifespan: safe startup & worker bootstrap ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Use FastAPI lifespan so background workers start after the async runtime
    (and SQLAlchemy/greenlet hooks) are fully initialized.
    """
    # give the event loop one tick so all greenlet hooks can attach reliably
    await asyncio.sleep(0)

    # start background workers as tasks (they must be async functions)
    hold_task = asyncio.create_task(run_hold_release_scheduler(interval_seconds=60))
    hourly_task = asyncio.create_task(run_hourly_booking_lifecycle_scheduler(interval_seconds=3600))
    daily_task = asyncio.create_task(run_daily_checkout_scheduler_at_1159pm())
    offers_task = asyncio.create_task(run_offer_expiry_scheduler_at_1159pm())

    app.state._worker_tasks = [hold_task, hourly_task, daily_task, offers_task]
    _logger.info("[LIFESPAN] Background workers started safely")

    try:
        yield  # app is running
    finally:
        # graceful shutdown: cancel worker tasks on app shutdown
        for t in getattr(app.state, "_worker_tasks", []):
            t.cancel()
        _logger.info("[LIFESPAN] Background workers cancelled on shutdown")


# -------------------------------------------------
# ✅ FastAPI App Configuration
# -------------------------------------------------
app = FastAPI(
    title="Hotel Booking System API",
    version="1.0.0",
    description="Hybrid Hotel Booking Platform (PostgreSQL + MongoDB)",
    openapi_url="/openapi.json",
    docs_url=None,
    redoc_url="/redoc",
    lifespan=lifespan,   # <- important
)

# -------------------------------------------------
# ✅ Middlewares
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200","http://localhost:63981"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# -------------------------------------------------
# ✅ Routers
# -------------------------------------------------
app.include_router(roles_and_permissions_router)
app.include_router(auth_router)
app.include_router(room_management_router)
app.include_router(booking_customer_router)
app.include_router(wishlist_router)
app.include_router(notifications_router)
app.include_router(issue_router)
app.include_router(reviews_router)
app.include_router(refunds_router)
app.include_router(profile_router)
app.include_router(backups_router)
app.include_router(logs_router)
app.include_router(restores_router)
app.include_router(reports_router)
app.include_router(content_router)
app.include_router(payment_router)
app.include_router(users_router)
app.include_router(v2_booking_router)
app.include_router(offers_router)
app.include_router(images_router)

@app.get("/docs", include_in_schema=False)
def custom_docs():
    """Serve custom Swagger UI from static HTML file"""
    html_file = Path(__file__).parent / "static" / "swagger_custom.html"
    return FileResponse(path=html_file, media_type="text/html")


# -------------------------------------------------
# ✅ Startup Events
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Run background workers when the app starts:
    1. Release expired room holds worker - runs every 60 seconds
    2. Booking lifecycle hourly worker - runs every hour to mark confirmed bookings as checked-in
    3. Room lifecycle daily worker - runs at 11:59 PM to mark checked-in bookings as checked-out
    """
    # Worker 1: Release expired room holds (every 60 seconds)
    asyncio.create_task(run_hold_release_scheduler(interval_seconds=60))
    _logger.info("[STARTUP] Room holds release worker started")
    
    # Worker 2: Hourly booking lifecycle updates (every 3600 seconds = 1 hour)
    asyncio.create_task(run_hourly_booking_lifecycle_scheduler(interval_seconds=3600))
    _logger.info("[STARTUP] Hourly booking lifecycle worker started")
    
    # Worker 3: Daily checkout at 11:59 PM
    asyncio.create_task(run_daily_checkout_scheduler_at_1159pm())
    _logger.info("[STARTUP] Daily checkout (11:59 PM) worker started")
    
    # Print out auth config (debug)
    try:
        _logger.info('Auth config - ACCESS_TOKEN_EXPIRE_MINUTES=%s REFRESH_TOKEN_EXPIRE_DAYS=%s', os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'), os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))
    except Exception:
        pass
