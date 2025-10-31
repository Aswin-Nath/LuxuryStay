from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.roles.roles import roles_router
from app.routes.permissions import permissions_router
from app.routes.auth.auth import auth_router
from app.routes.room_management import router as room_management_router
from app.routes.offers.offers import router as offers_router
from app.routes.booking import customer as booking_customer_router
from app.middlewares.error_handler import ErrorHandlerMiddleware
app = FastAPI()

# CORS setup for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend domain for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handling middleware for domain/service errors
app.add_middleware(ErrorHandlerMiddleware)

# Include routes
app.include_router(roles_router)
app.include_router(permissions_router)
app.include_router(auth_router)
app.include_router(room_management_router)
app.include_router(offers_router)
app.include_router(booking_customer_router.router)
from app.routes.issue_management import customer as issue_customer_router
from app.routes.issue_management import admin as issue_admin_router

app.include_router(issue_customer_router.router)
app.include_router(issue_admin_router.router)
