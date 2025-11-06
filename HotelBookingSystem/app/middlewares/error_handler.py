from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Callable
import traceback

from app.core.exceptions import APIError


async def error_handler_middleware(request: Request, call_next: Callable):
    """Function-style middleware that catches APIError and unexpected exceptions
    and returns JSON responses. Uses print() for minimal logging of tracebacks.
    """
    try:
        response = await call_next(request)
        return response
    except APIError as e:
        payload = {"detail": e.detail}
        return JSONResponse(status_code=getattr(e, "status_code", 500), content=payload)
    except Exception:
        # Unexpected error — return 500 but include no internal details in prod
        tb = traceback.format_exc()
        payload = {"detail": "Internal server error"}
        # Print traceback to stdout/stderr so it's visible in Uvicorn logs
        print("Unhandled exception:", tb)
        return JSONResponse(status_code=500, content=payload)


__all__ = ["error_handler_middleware"]
