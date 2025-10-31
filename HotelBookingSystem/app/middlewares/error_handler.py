from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Callable
import traceback

from app.core.exceptions import APIError


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to catch domain exceptions and convert them to JSON HTTP responses.

    This keeps routes and services free from FastAPI-specific error handling.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except APIError as e:
            payload = {"detail": e.detail}
            return JSONResponse(status_code=getattr(e, "status_code", 500), content=payload)
        except Exception as e:
            # Unexpected error — return 500 but include no internal details in prod
            tb = traceback.format_exc()
            # In dev you might want to include the traceback. Here we keep a minimal message.
            payload = {"detail": "Internal server error"}
            # Optionally log traceback
            print("Unhandled exception:", tb)
            return JSONResponse(status_code=500, content=payload)
