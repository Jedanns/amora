from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.monotonic()
        method = request.method
        path = request.url.path

        logger.info("request_started method=%s path=%s", method, path)

        response: Response = await call_next(request)  # type: ignore[call-arg]

        elapsed_ms = (time.monotonic() - start) * 1000.0
        logger.info(
            "request_completed method=%s path=%s status=%d duration_ms=%.1f",
            method,
            path,
            response.status_code,
            elapsed_ms,
        )

        response.headers["X-Request-Duration-Ms"] = f"{elapsed_ms:.1f}"
        return response
