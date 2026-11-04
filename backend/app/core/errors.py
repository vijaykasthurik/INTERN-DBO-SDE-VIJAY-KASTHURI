"""Standardized error models and global error handling for Lumen."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized API Error Envelope."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: dict[str, Any] | None = Field(default=None, description="Detailed contextual data")
    trace_id: str | None = Field(default=None, description="Trace or correlation identifier")


class LumenException(Exception):
    """Base exception for all Lumen domain and infrastructure errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(LumenException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(LumenException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(LumenException):
    def __init__(self, message: str = "Invalid credentials", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionDeniedError(LumenException):
    def __init__(self, message: str = "Access denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


async def lumen_exception_handler(request: Request, exc: LumenException) -> JSONResponse:
    """Handle custom Lumen exceptions uniformly."""
    trace_id = getattr(request.state, "trace_id", None)
    envelope = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    trace_id = getattr(request.state, "trace_id", None)
    envelope = ErrorResponse(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred",
        details={"raw": str(exc)} if str(exc) else None,
        trace_id=trace_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump(),
    )
