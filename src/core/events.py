from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

EventHandler = Callable[["GameEvent"], Coroutine[Any, Any, None]]


class EventType(StrEnum):
    STATE_CHANGED = "state_changed"
    DICE_ROLLED = "dice_rolled"
    CHARACTER_UPDATED = "character_updated"
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    ITEM_EQUIPPED = "item_equipped"
    ITEM_UNEQUIPPED = "item_unequipped"
    CONDITION_APPLIED = "condition_applied"
    CONDITION_REMOVED = "condition_removed"
    QUEST_STARTED = "quest_started"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    COMBAT_STARTED = "combat_started"
    COMBAT_ENDED = "combat_ended"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    SESSION_CREATED = "session_created"
    SESSION_SAVED = "session_saved"
    SESSION_LOADED = "session_loaded"
    LORE_INJECTED = "lore_injected"
    LLM_REQUEST_SENT = "llm_request_sent"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    ERROR_OCCURRED = "error_occurred"


@dataclass(frozen=True)
class GameEvent:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = ""


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def subscribe(
        self, event_type: EventType, handler: EventHandler
    ) -> Callable[[], None]:
        self._handlers[event_type].append(handler)

        def unsubscribe() -> None:
            self._handlers[event_type].remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: EventHandler) -> Callable[[], None]:
        self._global_handlers.append(handler)

        def unsubscribe() -> None:
            self._global_handlers.remove(handler)

        return unsubscribe

    async def emit(self, event: GameEvent) -> None:
        handlers = [
            *self._handlers.get(event.type, []),
            *self._global_handlers,
        ]
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for _i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler error: %s for event %s",
                    result,
                    event.type.value,
                    exc_info=result,
                )

    def clear(self) -> None:
        self._handlers.clear()
        self._global_handlers.clear()
