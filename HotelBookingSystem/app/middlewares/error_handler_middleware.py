"""
Simple Global Error Handling Middleware

Catches all exceptions and converts them to JSON responses.
"""

import logging
import traceback
from typing import Callable

from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Generic error handling middleware that catches all exceptions
    and returns them as JSON responses.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return self.handle_exception(request, exc)

    def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Handle any exception and return a JSON error response.
        
        Args:
            request (Request): The incoming HTTP request
            exc (Exception): The exception that was raised
            
        Returns:
            JSONResponse: Error response
        """
        # Get exception details
        exc_type = type(exc).__name__
        exc_message = str(exc)
        
        # Determine status code
        if isinstance(exc, HTTPException):
            status_code = exc.status_code
            error_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_msg = exc_message

        # Log the error
        method = request.method
        path = str(request.url.path)
        client = request.client.host if request.client else "unknown"
        
        log_message = f"[ERROR] {method} {path} | {exc_type}: {error_msg} | Client: {client}"
        
        if status_code >= 500:
            logger.error(log_message)
            logger.error(f"[TRACEBACK]\n{traceback.format_exc()}")
        else:
            logger.warning(log_message)

        # Return error response
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": error_msg,
                "exception": exc_type,
                "path": path,
                "method": method,
            }
        )
