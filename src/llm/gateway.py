from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from src.core.config import LLMConfig, RetryConfig
from src.core.events import EventBus, EventType, GameEvent
from src.core.exceptions import (
    LLMConnectionError,
    LLMContentFilterError,
    LLMGenerationError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GenerationParams:
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    stop_sequences: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: LLMConfig) -> GenerationParams:
        return cls(
            max_tokens=config.max_response_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
        )


@dataclass(frozen=True)
class GenerationResult:
    text: str
    tokens_generated: int
    tokens_prompt: int
    duration_seconds: float
    model: str = ""
    finish_reason: str = "stop"
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_per_second(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return self.tokens_generated / self.duration_seconds


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> GenerationResult: ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    def count_tokens(self, text: str) -> int: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...

    @abstractmethod
    async def get_model_info(self) -> dict[str, Any]: ...

    @abstractmethod
    async def close(self) -> None: ...


class ResilientLLMGateway:
    def __init__(
        self,
        provider: LLMProvider,
        retry_config: RetryConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._retry = retry_config or RetryConfig()
        self._event_bus = event_bus
        self._request_count = 0
        self._total_tokens = 0

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> GenerationResult:
        await self._emit_request(prompt)
        last_error: Exception | None = None

        for attempt in range(self._retry.max_attempts):
            try:
                healthy = await self._provider.is_healthy()
                if not healthy:
                    raise LLMConnectionError(
                        "LLM provider is not healthy",
                        context={"attempt": attempt + 1},
                    )

                result = await self._provider.generate(prompt, params)
                self._request_count += 1
                self._total_tokens += result.tokens_generated
                await self._emit_response(result)

                await logger.ainfo(
                    "llm_generation_success",
                    attempt=attempt + 1,
                    tokens=result.tokens_generated,
                    duration=result.duration_seconds,
                    tps=result.tokens_per_second,
                )
                return result

            except LLMContentFilterError:
                raise

            except (
                LLMConnectionError,
                LLMGenerationError,
                ConnectionError,
                TimeoutError,
                OSError,
            ) as exc:
                last_error = exc
                delay = self._get_retry_delay(attempt)
                await logger.awarning(
                    "llm_generation_retry",
                    attempt=attempt + 1,
                    max_attempts=self._retry.max_attempts,
                    delay=delay,
                    error=str(exc),
                )
                if attempt < self._retry.max_attempts - 1:
                    await asyncio.sleep(delay)

        raise LLMGenerationError(
            f"Failed after {self._retry.max_attempts} retries",
            context={"last_error": str(last_error)},
        ) from last_error

    async def generate_stream(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> AsyncIterator[str]:
        healthy = await self._provider.is_healthy()
        if not healthy:
            raise LLMConnectionError("LLM provider is not healthy")

        await self._emit_request(prompt)
        return self._provider.generate_stream(prompt, params)

    def count_tokens(self, text: str) -> int:
        return self._provider.count_tokens(text)

    async def is_healthy(self) -> bool:
        return await self._provider.is_healthy()

    async def close(self) -> None:
        await self._provider.close()

    def _get_retry_delay(self, attempt: int) -> float:
        delays = self._retry.delay_seconds
        if attempt < len(delays):
            return delays[attempt]
        return delays[-1] if delays else 1.0

    async def _emit_request(self, prompt: str) -> None:
        if self._event_bus:
            event = GameEvent(
                type=EventType.LLM_REQUEST_SENT,
                data={
                    "prompt_length": len(prompt),
                    "prompt_tokens": self._provider.count_tokens(prompt),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                source="llm_gateway",
            )
            await self._event_bus.emit(event)

    async def _emit_response(self, result: GenerationResult) -> None:
        if self._event_bus:
            event = GameEvent(
                type=EventType.LLM_RESPONSE_RECEIVED,
                data={
                    "tokens_generated": result.tokens_generated,
                    "duration_seconds": result.duration_seconds,
                    "tokens_per_second": result.tokens_per_second,
                    "finish_reason": result.finish_reason,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                source="llm_gateway",
            )
            await self._event_bus.emit(event)
