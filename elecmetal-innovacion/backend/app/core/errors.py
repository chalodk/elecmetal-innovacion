"""Centralized error handling for the Elecmetal Innovacion API.

All API errors follow the unified format:
  {"error": {"code": "ERROR_CODE", "message": "Human-readable description", "details": {...}}}

Usage:
  raise AppError(code=ErrorCode.NOT_FOUND, message="Iniciativa no encontrada")

The exception handler registered in main.py converts AppError to a proper
JSON response and logs the error. Unhandled exceptions get a generic 500.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ── Error codes ──────────────────────────────────────────────────────────────

class ErrorCode(str, Enum):
    """Canonical error codes for the unified error format."""

    # 400 — Bad request
    INVALID_ID = "INVALID_ID"

    # 401 — Authentication
    UNAUTHORIZED = "UNAUTHORIZED"

    # 403 — Authorization
    FORBIDDEN = "FORBIDDEN"

    # 404 — Not found
    NOT_FOUND = "NOT_FOUND"

    # 409 — Conflict (state machine violations)
    STATE_CONFLICT = "STATE_CONFLICT"

    # 422 — Validation / unprocessable
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_AGENT_TYPE = "INVALID_AGENT_TYPE"
    DBI_PARSE_ERROR = "DBI_PARSE_ERROR"

    # 502 — Upstream failure (OpenAI, etc.)
    EVALUATOR_ERROR = "EVALUATOR_ERROR"

    # 500 — Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ── Status code mapping ─────────────────────────────────────────────────────

_CODE_STATUS: dict[ErrorCode, int] = {
    ErrorCode.INVALID_ID: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.STATE_CONFLICT: 409,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.INVALID_AGENT_TYPE: 422,
    ErrorCode.DBI_PARSE_ERROR: 422,
    ErrorCode.EVALUATOR_ERROR: 502,
    ErrorCode.INTERNAL_ERROR: 500,
}


# ── Application error ───────────────────────────────────────────────────────

class AppError(Exception):
    """Application-level error that maps to the unified API error format.

    Args:
        code: One of ErrorCode enum values.
        message: Human-readable description (Spanish preferred).
        details: Optional dict with extra context (field names, values, etc.).
        status_code: Optional override for the HTTP status. Defaults to the
                     canonical code for the given ErrorCode.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code or _CODE_STATUS.get(code, 500)


# ── FastAPI exception handler ───────────────────────────────────────────────

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Converts an AppError into the unified JSON error response."""
    logger.warning(
        "app_error code=%s message=%s path=%s",
        exc.code, exc.message, request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions. Returns generic 500."""
    logger.exception(
        "unhandled_error type=%s path=%s",
        type(exc).__name__, request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Error interno del servidor",
                "details": {},
            }
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Converts FastAPI HTTPException to the unified error format."""
    from fastapi.exceptions import HTTPException as FastAPIHTTPException

    if isinstance(exc, FastAPIHTTPException):
        http_exc: FastAPIHTTPException = exc
        code = _http_status_to_code(http_exc.status_code)
        return JSONResponse(
            status_code=http_exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(http_exc.detail),
                    "details": {},
                }
            },
        )
    return await unhandled_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Converts FastAPI/pydantic validation errors (422) to the unified format."""
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        # Build field-level details from pydantic errors
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            field_errors.setdefault(loc, []).append(msg)

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": "Datos enviados invalidos — revisa los detalles",
                    "details": {"fields": field_errors},
                }
            },
        )

    # Fallback
    return await unhandled_exception_handler(request, exc)


def _http_status_to_code(status_code: int) -> str:
    """Map HTTP status to an ErrorCode string."""
    mapping = {
        400: ErrorCode.INVALID_ID,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.STATE_CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)
