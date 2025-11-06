from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.middleware.cors import CORSMiddleware

from app.middlewares.error_handler import error_handler_middleware
from app.middlewares.logging_middleware import logging_middleware
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


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(error_handler_middleware)
app.middleware("http")(logging_middleware)


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

