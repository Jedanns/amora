from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.deps import get_app_state, initialize_app_state, shutdown_app_state
from src.api.middleware.error_handler import (
    generic_exception_handler,
    rpg_exception_handler,
)
from src.api.middleware.request_logger import RequestLoggerMiddleware
from src.api.routes import character, game, llm, lore
from src.api.schemas.responses import HealthCheckResponse
from src.core.config import load_config
from src.core.exceptions import RPGEngineError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _start_time
    _start_time = time.monotonic()

    cfg = load_config()
    await initialize_app_state(cfg)
    logger.info("RPG Engine API started on %s:%d", cfg.api.host, cfg.api.port)

    yield

    await shutdown_app_state()
    logger.info("RPG Engine API shut down")


def create_app() -> FastAPI:
    cfg = load_config()

    app = FastAPI(
        title="Mon RPG IA - API",
        description="AI-powered RPG engine REST API",
        version=cfg.app.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggerMiddleware)

    app.add_exception_handler(RPGEngineError, rpg_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    app.include_router(game.router, prefix="/api")
    app.include_router(character.router, prefix="/api")
    app.include_router(lore.router, prefix="/api")
    app.include_router(llm.router, prefix="/api")

    @app.get("/health", response_model=HealthCheckResponse, tags=["system"])
    async def health_check() -> HealthCheckResponse:
        uptime = time.monotonic() - _start_time if _start_time > 0 else 0.0
        state = get_app_state()
        return HealthCheckResponse(
            status="ok",
            version=state.config.app.version,
            uptime_seconds=uptime,
        )

    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.is_dir():
        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

        app.mount(
            "/static",
            StaticFiles(directory=str(static_dir)),
            name="static",
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    uvicorn.run(
        "src.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.app.debug,
        log_level="info",
    )
