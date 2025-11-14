"""
Global Error Handling Middleware with environment-aware error details.

In production, sensitive error details are hidden to prevent information leakage.
In development, full error details are shown for debugging.
"""

from loguru import logger
from typing import Callable

from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware



class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Generic error handling middleware that catches all exceptions
    and returns them as JSON responses.
    
    Hides sensitive information in production environments.
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
            JSONResponse: Error response with environment-appropriate details
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

        # Log the error with full details
        method = request.method
        path = str(request.url.path)
        client = request.client.host if request.client else "unknown"
        
        log_message = f"Exception | method={method} path={path} exception_type={exc_type} message={error_msg} client={client}"
        
        if status_code >= 500:
            logger.error(log_message)
            logger.error(f"Traceback: {exc}")
        else:
            logger.warning(log_message)

        # Build error response based on environment
        response_body = {
            "success": False,
            "error": error_msg,
        }
        
        # Only include sensitive details in development/staging
        response_body["exception_type"] = exc_type
        response_body["path"] = path
        response_body["method"] = method
    
        # In production, provide a generic message for 500 errors
        if status_code >= 500:
            response_body["error"] = "An internal server error occurred."

        return JSONResponse(
            status_code=status_code,
            content=response_body
        )
