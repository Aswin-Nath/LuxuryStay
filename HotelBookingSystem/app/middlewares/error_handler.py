from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Callable
import traceback
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import APIError


async def error_handler_middleware(request: Request, call_next: Callable):
    """Function-style middleware that catches APIError, database errors, and unexpected exceptions
    and returns JSON responses. Uses print() for minimal logging of tracebacks.
    """
    try:
        response = await call_next(request)
        return response
    except APIError as e:
        payload = {"detail": e.detail}
        return JSONResponse(status_code=getattr(e, "status_code", 500), content=payload)
    except IntegrityError as e:
        # Handle database integrity constraint violations
        tb = traceback.format_exc()
        print("IntegrityError:", tb)
        
        # Parse common foreign key violations
        error_str = str(e)
        if "refund_room_map_room_id_fkey" in error_str:
            payload = {"detail": "One or more rooms in this booking no longer exist. Cannot process refund."}
            return JSONResponse(status_code=400, content=payload)
        elif "refund_room_map_booking_id_fkey" in error_str:
            payload = {"detail": "The booking reference is invalid. Cannot process refund."}
            return JSONResponse(status_code=400, content=payload)
        elif "foreign key constraint" in error_str.lower():
            payload = {"detail": "Failed to process request due to invalid reference. Please verify all IDs are correct."}
            return JSONResponse(status_code=400, content=payload)
        elif "unique constraint" in error_str.lower():
            payload = {"detail": "This resource already exists. Please use a different value."}
            return JSONResponse(status_code=409, content=payload)
        else:
            payload = {"detail": "Data consistency error. Please contact support."}
            return JSONResponse(status_code=400, content=payload)
    except Exception as e:
        # Unexpected error — return 500 but include no internal details in prod
        tb = traceback.format_exc()
        payload = {"detail": "Internal server error"}
        # Print traceback to stdout/stderr so it's visible in Uvicorn logs
        print("Unhandled exception:", tb)
        return JSONResponse(status_code=500, content=payload)


__all__ = ["error_handler_middleware"]
