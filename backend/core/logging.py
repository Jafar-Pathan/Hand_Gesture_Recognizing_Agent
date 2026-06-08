"""
Structured JSON logging and request-logging middleware.

Configures the root logger to emit JSON-formatted records and provides a
Starlette middleware that logs every HTTP request with method, path, status
code, and response duration.
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import settings


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Logging formatter that outputs each record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach exception info when present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Forward any extra fields attached by callers
        for key in ("request_id", "user_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """Configure the root logger with the JSON formatter.

    Should be called once during application startup.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid duplicate handlers on repeated calls (e.g. during tests)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_json_configured", False) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        handler._json_configured = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Request-logging middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every inbound HTTP request and its response status.

    Logs include HTTP method, path, response status code, and wall-clock
    duration in milliseconds.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        logger = logging.getLogger("backend.middleware.request")
        start_time = time.perf_counter()

        # Process the request
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Unhandled exception for %s %s (%.2f ms)",
                request.method,
                request.url.path,
                duration_ms,
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            "%s %s → %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


# ---------------------------------------------------------------------------
# Error tracking helper
# ---------------------------------------------------------------------------

def log_error(
    error: Exception,
    *,
    context: str = "",
    user_id: int | None = None,
) -> None:
    """Log an exception with optional context information.

    This is a convenience wrapper so callers don't need to remember to pass
    ``exc_info``.

    Args:
        error: The caught exception.
        context: A short human-readable description of what was happening.
        user_id: Optional user id for correlation.
    """
    logger = logging.getLogger("backend.error")
    logger.error(
        "Error in %s: %s",
        context or "unknown context",
        str(error),
        exc_info=error,
        extra={"user_id": user_id},
    )
