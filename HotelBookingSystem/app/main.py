from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.middlewares.logging_middleware import logging_middleware

from app.routes.roles_and_permissions import roles_and_permissions_router
from app.routes.authentication import auth_router
from app.routes.room_management import router as room_management_router
from app.routes.offers import router as offers_router
from app.routes.booking import router as booking_customer_router
from app.routes.wishlist import router as wishlist_router
from app.routes.notifications import router as notifications_router
from app.routes.issues import router as issue_router
from app.routes.reviews import router as reviews_router
from app.routes.refund import router as refunds_router
from app.routes.edit_booking import router as booking_edits_router
from app.routes.profile import router as profile_router
from app.routes.logs import router as logs_router
from app.routes.backups import router as backups_router
from app.routes.restores import router as restores_router
from app.routes.reports import router as reports_router
from app.routes.content import router as content_router
from app.routes.payments import router as payment_router

# -------------------------------------------------
# ✅ FastAPI App Configuration
# -------------------------------------------------
app = FastAPI(
    title="Hotel Booking System API",
    version="1.0.0",
    description="Hybrid Hotel Booking Platform (PostgreSQL + MongoDB)",
    openapi_url="/openapi.json",
    docs_url=None,         # disable default /docs
    redoc_url="/redoc",    # keep redoc enabled
)

# -------------------------------------------------
# ✅ Middlewares
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(logging_middleware)

# -------------------------------------------------
# ✅ Routers
# -------------------------------------------------
app.include_router(roles_and_permissions_router)
app.include_router(auth_router)
app.include_router(room_management_router)
app.include_router(offers_router)
app.include_router(booking_customer_router)
app.include_router(wishlist_router)
app.include_router(notifications_router)
app.include_router(issue_router)
app.include_router(reviews_router)
app.include_router(refunds_router)
app.include_router(booking_edits_router)
app.include_router(profile_router)
app.include_router(backups_router)
app.include_router(logs_router)
app.include_router(restores_router)
app.include_router(reports_router)
app.include_router(content_router)
app.include_router(payment_router)

@app.get("/docs", include_in_schema=False)
def custom_docs():
    """Serve custom Swagger UI from static HTML file"""
    html_file = Path(__file__).parent / "static" / "swagger_custom.html"
    return FileResponse(path=html_file, media_type="text/html")
