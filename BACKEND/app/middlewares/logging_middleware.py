from time import time
from typing import Callable
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request payload, response info, and execution time."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time()

        method = request.method
        path = request.url.path
        query = request.url.query
        client = request.client.host if request.client else "-"

        # --- 🔥 Read AND restore request body ---
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="ignore")

        # recreate stream so FastAPI routes can still read body
        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request._receive = receive

        # --- Process request ---
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time() - start) * 1000)
            logger.error(
                f"❌ Request error "
                f"| method={method} path={path} query={query} client={client} "
                f"duration_ms={duration_ms} exception={exc} body={body_text}"
            )
            raise

        # --- Response info ---
        duration_ms = int((time() - start) * 1000)
        status = response.status_code
        content_length = response.headers.get("content-length", "-")

        # --- Log with payload ---
        logger.info(
            f"➡️ API Request | method={method} path={path} query={query} client={client} "
            f"status={status} content_length={content_length} duration_ms={duration_ms} "
            f"body={body_text}"
        )

        return response
