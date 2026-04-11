from time import time
from typing import Callable
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import os

ENV = os.getenv("ENV", "development")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request info WITHOUT blocking the response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "-"

        # --- Process request immediately (don't read body) ---
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time() - start) * 1000)
            logger.error(f"❌ Request error | method={method} path={path} client={client} duration_ms={duration_ms}")
            raise

        # --- Calculate duration ---
        duration_ms = int((time() - start) * 1000)
        status = response.status_code

        # --- Log asynchronously in background (non-blocking) ---
        if duration_ms > 3000 or status >= 400:
            # Log slow requests or errors immediately
            logger.warning(
                f"⚠️ API {'ERROR' if status >= 400 else 'SLOW'} | method={method} path={path} "
                f"status={status} client={client} duration_ms={duration_ms}"
            )
        elif ENV == "development":
            # Only log all requests in development
            asyncio.create_task(self._log_async(method, path, status, duration_ms))

        return response

    async def _log_async(self, method: str, path: str, status: int, duration_ms: int):
        """Log in background without blocking response."""
        try:
            logger.info(f"✓ API | method={method} path={path} status={status} duration_ms={duration_ms}")
        except Exception:
            pass
