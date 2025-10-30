from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.images.image import image_router
from app.routes.roles.roles import roles_router
from app.routes.permissions import permissions_router
from app.routes.auth.auth import auth_router
app = FastAPI()

# CORS setup for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend domain for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(image_router)
app.include_router(roles_router)
app.include_router(permissions_router)
app.include_router(auth_router)