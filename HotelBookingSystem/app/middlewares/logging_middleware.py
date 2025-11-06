from time import time
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response


async def logging_middleware(request: Request, call_next: Callable) -> Response:
	"""Function-style middleware that prints basic request/response info and time taken.

	Uses plain print() calls (per request) instead of the logging module.
	"""
	start = time()

	method = request.method
	path = request.url.path
	query = str(request.url.query) if request.url.query else ""
	client = request.client.host if request.client else "-"

	try:
		response = await call_next(request)
	except Exception as exc:
		duration_ms = int((time() - start) * 1000)
		print(f"[REQUEST ERROR] method={method} path={path} query={query} client={client} duration_ms={duration_ms} exception={exc}")
		raise

	duration_ms = int((time() - start) * 1000)
	status = response.status_code
	content_length = response.headers.get("content-length", "-")

	print(
		f"[API] method={method} path={path} query={query} client={client} status={status} content_length={content_length} duration_ms={duration_ms}"
	)

	return response


__all__ = ["logging_middleware"]
