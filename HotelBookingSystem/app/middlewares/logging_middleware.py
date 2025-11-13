from time import time
from typing import Callable
from loguru import logger

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
	"""Middleware that logs basic request/response info and time taken."""

	async def dispatch(self, request: Request, call_next: Callable) -> Response:
		"""Process request and log timing/status information."""
		start = time()

		method = request.method
		path = request.url.path
		query = str(request.url.query) if request.url.query else ""
		client = request.client.host if request.client else "-"

		try:
			response = await call_next(request)
		except Exception as exc:
			duration_ms = int((time() - start) * 1000)
			logger.error(f"Request error | method={method} path={path} query={query} client={client} duration_ms={duration_ms} exception={exc}")
			raise

		duration_ms = int((time() - start) * 1000)
		status = response.status_code
		content_length = response.headers.get("content-length", "-")

		logger.info(
			f"API request | method={method} path={path} query={query} client={client} status={status} content_length={content_length} duration_ms={duration_ms}"
		)

		return response

