from __future__ import annotations

import asyncio

import pytest

from src.llm.mock import MockLLMProvider
from src.llm.streaming import (
    StreamBuffer,
    StreamMetrics,
    collect_stream,
    stream_to_queue,
)


class TestStreamMetrics:
    def test_default_values(self) -> None:
        metrics = StreamMetrics()
        assert metrics.tokens_received == 0
        assert metrics.first_token_time is None
        assert metrics.total_time == 0.0
        assert metrics.tokens_per_second == 0.0
        assert metrics.time_to_first_token is None

    def test_tokens_per_second(self) -> None:
        metrics = StreamMetrics(tokens_received=100, total_time=2.0)
        assert metrics.tokens_per_second == 50.0

    def test_tokens_per_second_zero_time(self) -> None:
        metrics = StreamMetrics(tokens_received=10, total_time=0.0)
        assert metrics.tokens_per_second == 0.0


class TestStreamBuffer:
    def test_append(self) -> None:
        buf = StreamBuffer()
        buf.append("Hello")
        buf.append(" world")
        assert buf.text == "Hello world"
        assert buf.content == "Hello world"
        assert len(buf.tokens) == 2
        assert buf.metrics.tokens_received == 2

    def test_empty_buffer(self) -> None:
        buf = StreamBuffer()
        assert buf.text == ""
        assert buf.metrics.tokens_received == 0


class TestCollectStream:
    @pytest.mark.asyncio
    async def test_collect_from_mock(self) -> None:
        provider = MockLLMProvider(responses=["Hello world how are you"])
        stream = provider.generate_stream("test")
        buffer = await collect_stream(stream)
        assert "Hello" in buffer.text
        assert buffer.metrics.tokens_received > 0
        assert buffer.metrics.first_token_time is not None
        assert buffer.metrics.total_time >= 0

    @pytest.mark.asyncio
    async def test_collect_with_callback(self) -> None:
        collected: list[str] = []

        def cb(token: str) -> None:
            collected.append(token)

        provider = MockLLMProvider(responses=["One two three"])
        stream = provider.generate_stream("test")
        buffer = await collect_stream(stream, callback=cb)
        assert len(collected) == buffer.metrics.tokens_received

    @pytest.mark.asyncio
    async def test_collect_empty_stream(self) -> None:
        async def empty_gen():
            return
            yield

        buffer = await collect_stream(empty_gen())
        assert buffer.text == ""
        assert buffer.metrics.tokens_received == 0


class TestStreamToQueue:
    @pytest.mark.asyncio
    async def test_stream_to_queue(self) -> None:
        provider = MockLLMProvider(responses=["Alpha beta gamma"])
        stream = provider.generate_stream("test")
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        metrics = await stream_to_queue(stream, queue)
        assert metrics.tokens_received > 0

        tokens: list[str] = []
        while True:
            item = await queue.get()
            if item is None:
                break
            tokens.append(item)
        assert len(tokens) == metrics.tokens_received

    @pytest.mark.asyncio
    async def test_stream_to_queue_sends_sentinel(self) -> None:
        async def empty_gen():
            return
            yield

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        await stream_to_queue(empty_gen(), queue)
        item = await queue.get()
        assert item is None
