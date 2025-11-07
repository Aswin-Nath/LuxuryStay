from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.middlewares.error_handler import error_handler_middleware
from app.middlewares.logging_middleware import logging_middleware

from app.routes.roles_and_permissions_management.roles_and_permissions import roles_and_permissions_router
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
from app.routes.logs_management.audit_logs import router as audit_logs_router
from app.routes.logs_management.booking_logs import router as booking_logs_router
from app.routes.backup_and_restore_management.backups import router as backups_router
from app.routes.backup_and_restore_management.restores import router as restores_router


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

app.middleware("http")(error_handler_middleware)
app.middleware("http")(logging_middleware)


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
app.include_router(audit_logs_router)
app.include_router(booking_logs_router)
app.include_router(restores_router)


# -------------------------------------------------
# ✅ Custom Swagger UI Endpoint with Tag Filter + Field Rename
# -------------------------------------------------
@app.get("/docs", include_in_schema=False)
def custom_docs():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <title>Hotel Booking System API Docs</title>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>

        <script>
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            layout: 'BaseLayout',
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            onComplete: () => {
                // Rename username/password fields → Mobile/OTP dynamically
                setInterval(() => {
                    const modal = document.querySelector('.modal-ux');
                    if (!modal) return;
                    modal.querySelectorAll('*').forEach(el => {
                        el.childNodes.forEach(node => {
                            if (node.nodeType === 3) {
                                const text = node.textContent.trim();
                                if (text.includes('username')) {
                                    node.textContent = text.replace(/username/gi, 'Mobile');
                                }
                                if (text.includes('password')) {
                                    node.textContent = text.replace(/password/gi, 'OTP');
                                }
                            }
                        });
                    });
                }, 1000);

                // Add a dropdown filter by API tag
                setTimeout(() => {
                    const authWrapper = document.querySelector('.auth-wrapper');
                    if (authWrapper) {
                        const dropdown = document.createElement('select');
                        dropdown.innerHTML = `
                            <option value=""> Show All </option>
                            <option value="ROLES">Roles</option>
                            <option value="Auth">Auth</option>
                            <option value="Rooms">Rooms</option>
                            <option value="Amenities">Amenties</option>
                            <option value="Room_types">Room Types</option>
                            <option value="Rooms_images">Room Images</option>

                            <option value="wishlist">Wishlist</option>

                            <option value="Profile">Profile</option>
                            <option value="Offers">Offers</option>
                            <option value="Bookings">Bookings</option>
                            <option value="Booking-Edits">Edit Booking</option>
                            <option value="Refunds">Refunds</option>
                            <option value="Issues">Issues</option>
                            <option value="Reviews">Reviews</option>
                            <option value="Notifications">Notifications</option>
                            <option value="Backups">Backups</option>
                            <option value="Restores">Restores</option>
                            <option value="Logs">Logs</option>
                        `;

                        dropdown.style.marginRight = '20px';
                        dropdown.style.padding = '8px';
                        dropdown.style.border = '1px solid #ccc';
                        dropdown.style.borderRadius = '6px';
                        dropdown.style.cursor = 'pointer';
                        dropdown.style.backgroundColor = '#f5f5f5';
                        dropdown.style.width='400px'
                        dropdown.onchange = function() {
                            const tag = this.value;
                            document.querySelectorAll('.opblock-tag-section').forEach(sec => {
                                // compare case-insensitively by normalizing both sides to lower-case
                                const tagName = sec.querySelector('.opblock-tag').textContent.trim().toLowerCase();
                                const selected = tag ? tag.toLowerCase() : '';
                                sec.style.display = (!selected || tagName === selected) ? '' : 'none';
                            });
                        };

                        authWrapper.parentNode.insertBefore(dropdown, authWrapper);
                    }
                }, 300);
            }
        });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
