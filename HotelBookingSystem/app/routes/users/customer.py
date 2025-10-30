# app/routes/users.py
from fastapi import APIRouter, Depends
from app.core.security import oauth2_scheme

user_router = APIRouter(prefix="/users", tags=["USERS"])

@user_router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Example protected endpoint that requires a valid Bearer token.
    """
    return {"token_received": token}
