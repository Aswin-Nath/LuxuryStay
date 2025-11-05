from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.middleware.cors import CORSMiddleware
import pathlib

from app.middlewares.error_handler import ErrorHandlerMiddleware
from app.routes.roles_and_permissions_management.roles import roles_router
from app.routes.roles_and_permissions_management.permissions import permissions_router
from app.routes.authentication.authentication import auth_router
from app.routes.room_management import router as room_management_router
from app.routes.offer_management.offers import router as offers_router
from app.routes.booking_management.booking import router as booking_customer_router
from app.routes.wishlist_management.wishlist import router as wishlist_router
from app.routes.notifications_management.notifications import router as notifications_router
from app.routes.issue_management.issues import router as issue_router
from app.routes.reviews_management.reviews import router as reviews_router
from app.routes.refund_management.refund import router as refunds_router
from app.routes.booking_management.edit_booking import router as booking_edits_router
from app.routes.profile_management.profile import router as profile_router


# ===============================================================
# 🚀 FastAPI Initialization (Disable defaults)
# ===============================================================
app = FastAPI(
    title="Hotel Booking System API",
    version="0.1.0",
    docs_url=None,        # disable FastAPI's default Swagger
    redoc_url=None,       # disable ReDoc
    openapi_url="/openapi.json"
)

# ===============================================================
# 📂 Static Directory
# ===============================================================
BASE_DIR = pathlib.Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

print(f"✅ Static directory mounted at: {STATIC_DIR}")

# ===============================================================
# 🧭 Custom Swagger UI (temporary route name for testing)
# ===============================================================
@app.get("/custom-docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_path = STATIC_DIR / "swagger_custom.html"
    print(f"📄 Loading Swagger UI from: {html_path}")

    if not html_path.exists():
        print("❌ swagger_custom.html not found!")
        return HTMLResponse("<h2>swagger_custom.html not found</h2>", status_code=404)

    content = html_path.read_text(encoding="utf-8")
    print("✅ swagger_custom.html loaded successfully.")
    return HTMLResponse(content, media_type="text/html")


@app.get("/custom-docs/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


# ===============================================================
# 🔐 Middleware Configuration
# ===============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorHandlerMiddleware)

# ===============================================================
# 🧩 Router Registration
# ===============================================================
app.include_router(roles_router)
app.include_router(permissions_router)
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

# ===============================================================
# 🩵 Health Check / Root Endpoint
# ===============================================================
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Hotel Booking System API running successfully. Visit /custom-docs for Swagger UI."}

