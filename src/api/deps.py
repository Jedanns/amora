from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.core.config import Config, load_config
from src.core.engine import GameEngine
from src.core.events import EventBus
from src.llm.gateway import ResilientLLMGateway
from src.llm.mock import MockLLMProvider
from src.llm.providers.koboldcpp import KoboldCPPProvider
from src.lore.book import Lorebook
from src.memory.context import ContextManager
from src.memory.summary import Summarizer
from src.persistence.database import Database

if TYPE_CHECKING:
    from src.llm.gateway import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    config: Config = field(default_factory=lambda: load_config())
    engine: GameEngine | None = None
    llm_gateway: ResilientLLMGateway | None = None
    llm_provider: LLMProvider | None = None
    lorebook: Lorebook | None = None
    context_manager: ContextManager | None = None
    summarizer: Summarizer | None = None
    event_bus: EventBus = field(default_factory=EventBus)
    _metadata: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)


_app_state: AppState | None = None


def get_app_state() -> AppState:
    if _app_state is None:
        msg = "App state not initialized. Call initialize_app_state() first."
        raise RuntimeError(msg)
    return _app_state


async def initialize_app_state(config: Config | None = None) -> AppState:
    global _app_state
    cfg = config or load_config()

    db = Database(cfg.persistence.database)
    engine = GameEngine(config=cfg, database=db)
    await engine.initialize()

    provider: LLMProvider
    if cfg.llm.provider == "koboldcpp":
        provider = KoboldCPPProvider(url=cfg.llm.url)
        logger.info("Using KoboldCPP provider at %s", cfg.llm.url)
    else:
        provider = MockLLMProvider()
        logger.info("Using mock LLM provider (provider=%s)", cfg.llm.provider)

    gateway = ResilientLLMGateway(
        provider=provider,
        retry_config=cfg.llm.retry,
        event_bus=engine.events,
    )

    lorebook = Lorebook()
    try:
        from pathlib import Path

        lore_dir = Path(cfg.lore.directory)
        if lore_dir.exists():
            lorebook.load_from_directory(str(lore_dir))
            logger.info(
                "Loaded lore from %s (%d entries)", lore_dir, lorebook.entry_count
            )
    except Exception:
        logger.warning("Failed to load lorebook directory", exc_info=True)

    context_mgr = ContextManager(
        max_context_tokens=cfg.memory.max_context_tokens,
        max_response_tokens=cfg.llm.max_response_tokens,
    )

    summarizer = Summarizer(
        summary_threshold=cfg.memory.summary_threshold,
        summary_every=cfg.memory.summary_every,
        max_summary_tokens=cfg.memory.summary_max_tokens,
    )

    _app_state = AppState(
        config=cfg,
        engine=engine,
        llm_gateway=gateway,
        llm_provider=provider,
        lorebook=lorebook,
        context_manager=context_mgr,
        summarizer=summarizer,
        event_bus=engine.events,
    )

    logger.info("App state initialized")
    return _app_state


async def shutdown_app_state() -> None:
    global _app_state
    if _app_state and _app_state.engine:
        await _app_state.engine.shutdown()
    if _app_state and _app_state.llm_provider:
        await _app_state.llm_provider.close()
    _app_state = None
    logger.info("App state shut down")
