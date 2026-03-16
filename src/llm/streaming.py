from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StreamMetrics:
    tokens_received: int = 0
    first_token_time: float | None = None
    total_time: float = 0.0
    chunks: int = 0

    @property
    def tokens_per_second(self) -> float:
        if self.total_time <= 0:
            return 0.0
        return self.tokens_received / self.total_time

    @property
    def time_to_first_token(self) -> float | None:
        return self.first_token_time


StreamCallback = Callable[[str], None]


@dataclass
class StreamBuffer:
    content: str = ""
    tokens: list[str] = field(default_factory=list)
    metrics: StreamMetrics = field(default_factory=StreamMetrics)

    def append(self, token: str) -> None:
        self.content += token
        self.tokens.append(token)
        self.metrics.tokens_received += 1
        self.metrics.chunks += 1

    @property
    def text(self) -> str:
        return self.content


async def collect_stream(
    stream: AsyncIterator[str],
    callback: StreamCallback | None = None,
    timeout: float = 120.0,
) -> StreamBuffer:
    import time

    buffer = StreamBuffer()
    start_time = time.monotonic()

    try:
        async with asyncio.timeout(timeout):
            async for token in stream:
                now = time.monotonic()
                if buffer.metrics.first_token_time is None:
                    buffer.metrics.first_token_time = now - start_time

                buffer.append(token)

                if callback:
                    callback(token)

    except TimeoutError:
        logger.warning(
            "stream_timeout",
            tokens_received=buffer.metrics.tokens_received,
            timeout=timeout,
        )

    buffer.metrics.total_time = time.monotonic() - start_time
    return buffer


async def stream_to_queue(
    stream: AsyncIterator[str],
    queue: asyncio.Queue[str | None],
    timeout: float = 120.0,
) -> StreamMetrics:
    import time

    metrics = StreamMetrics()
    start_time = time.monotonic()

    try:
        async with asyncio.timeout(timeout):
            async for token in stream:
                now = time.monotonic()
                if metrics.first_token_time is None:
                    metrics.first_token_time = now - start_time

                metrics.tokens_received += 1
                metrics.chunks += 1
                await queue.put(token)

    except TimeoutError:
        logger.warning(
            "stream_to_queue_timeout",
            tokens_received=metrics.tokens_received,
            timeout=timeout,
        )
    finally:
        await queue.put(None)

    metrics.total_time = time.monotonic() - start_time
    return metrics
