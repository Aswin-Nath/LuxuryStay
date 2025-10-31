from typing import Any


class APIError(Exception):
	"""Base class for domain errors raised by services.

	Attributes:
		detail: human-readable error message
		status_code: HTTP status code to return
	"""

	status_code: int = 500

	def __init__(self, detail: Any = "Internal server error") -> None:
		super().__init__(detail)
		self.detail = detail


class NotFoundError(APIError):
	status_code = 404


class ConflictError(APIError):
	status_code = 409


class UnauthorizedError(APIError):
	status_code = 401


class BadRequestError(APIError):
	status_code = 400


class ForbiddenError(APIError):
	status_code = 403


class InternalServerError(APIError):
	status_code = 500

