from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    CharacterError,
    InventoryError,
    LLMError,
    LoreError,
    QuestError,
    RPGEngineError,
    SessionError,
    StateError,
    ValidationError,
)

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)

EXCEPTION_STATUS_MAP: dict[type, int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SessionError: status.HTTP_404_NOT_FOUND,
    StateError: status.HTTP_409_CONFLICT,
    CharacterError: status.HTTP_404_NOT_FOUND,
    InventoryError: status.HTTP_400_BAD_REQUEST,
    QuestError: status.HTTP_400_BAD_REQUEST,
    LoreError: status.HTTP_400_BAD_REQUEST,
    LLMError: status.HTTP_502_BAD_GATEWAY,
}


async def rpg_exception_handler(request: Request, exc: RPGEngineError) -> JSONResponse:
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    for exc_type, code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    logger.warning(
        "RPG engine error: %s (status=%d, path=%s)",
        exc,
        status_code,
        request.url.path,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "status_code": status_code,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception: %s (path=%s)",
        exc,
        request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred.",
            "status_code": 500,
        },
    )
