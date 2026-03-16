from __future__ import annotations

import pytest

from src.core.config import RetryConfig
from src.core.events import EventBus, EventType, GameEvent
from src.core.exceptions import (
    LLMConnectionError,
    LLMContentFilterError,
    LLMGenerationError,
)
from src.llm.gateway import GenerationParams, GenerationResult, ResilientLLMGateway
from src.llm.mock import MockLLMProvider


class TestGenerationParams:
    def test_default_values(self) -> None:
        params = GenerationParams()
        assert params.max_tokens == 512
        assert params.temperature == 0.7
        assert params.top_p == 0.9
        assert params.top_k == 40
        assert params.stop_sequences == []

    def test_from_config(self) -> None:
        from src.core.config import LLMConfig

        config = LLMConfig(
            max_response_tokens=1024,
            temperature=0.5,
            top_p=0.8,
            top_k=50,
        )
        params = GenerationParams.from_config(config)
        assert params.max_tokens == 1024
        assert params.temperature == 0.5
        assert params.top_p == 0.8
        assert params.top_k == 50

    def test_frozen(self) -> None:
        params = GenerationParams()
        with pytest.raises(AttributeError):
            params.max_tokens = 1024  # type: ignore[misc]


class TestGenerationResult:
    def test_tokens_per_second(self) -> None:
        result = GenerationResult(
            text="hello",
            tokens_generated=100,
            tokens_prompt=50,
            duration_seconds=2.0,
        )
        assert result.tokens_per_second == 50.0

    def test_tokens_per_second_zero_duration(self) -> None:
        result = GenerationResult(
            text="hello",
            tokens_generated=100,
            tokens_prompt=50,
            duration_seconds=0.0,
        )
        assert result.tokens_per_second == 0.0


class TestMockLLMProvider:
    @pytest.fixture
    def provider(self) -> MockLLMProvider:
        return MockLLMProvider(
            responses=[
                "Le garde vous regarde avec suspicion.",
                "Il hoche la tête et vous laisse passer.",
            ]
        )

    @pytest.mark.asyncio
    async def test_generate(self, provider: MockLLMProvider) -> None:
        result = await provider.generate("Hello")
        assert result.text == "Le garde vous regarde avec suspicion."
        assert result.tokens_generated > 0
        assert provider.call_count == 1
        assert provider.last_prompt == "Hello"

    @pytest.mark.asyncio
    async def test_generate_cycles_responses(self, provider: MockLLMProvider) -> None:
        r1 = await provider.generate("First")
        r2 = await provider.generate("Second")
        r3 = await provider.generate("Third")
        assert r1.text == "Le garde vous regarde avec suspicion."
        assert r2.text == "Il hoche la tête et vous laisse passer."
        assert r3.text == "Le garde vous regarde avec suspicion."
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_stream(self, provider: MockLLMProvider) -> None:
        tokens: list[str] = []
        async for token in provider.generate_stream("Hello"):
            tokens.append(token)
        assert len(tokens) > 0
        full_text = "".join(tokens).strip()
        assert "garde" in full_text

    @pytest.mark.asyncio
    async def test_is_healthy(self, provider: MockLLMProvider) -> None:
        assert await provider.is_healthy() is True
        provider.set_healthy(False)
        assert await provider.is_healthy() is False

    @pytest.mark.asyncio
    async def test_count_tokens(self, provider: MockLLMProvider) -> None:
        count = provider.count_tokens("Hello world")
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_model_info(self, provider: MockLLMProvider) -> None:
        info = await provider.get_model_info()
        assert info["provider"] == "mock"
        assert info["model"] == "mock-model"

    @pytest.mark.asyncio
    async def test_close(self, provider: MockLLMProvider) -> None:
        await provider.close()
        assert provider._closed is True

    @pytest.mark.asyncio
    async def test_prompts_tracked(self, provider: MockLLMProvider) -> None:
        await provider.generate("prompt1")
        await provider.generate("prompt2")
        assert provider.prompts == ["prompt1", "prompt2"]

    @pytest.mark.asyncio
    async def test_set_responses(self, provider: MockLLMProvider) -> None:
        provider.set_responses(["New response"])
        result = await provider.generate("test")
        assert result.text == "New response"
        assert provider.call_count == 1


class TestResilientLLMGateway:
    @pytest.fixture
    def provider(self) -> MockLLMProvider:
        return MockLLMProvider(responses=["Success response"])

    @pytest.fixture
    def gateway(self, provider: MockLLMProvider) -> ResilientLLMGateway:
        return ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=3, delay_seconds=[0.0, 0.0, 0.0]),
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, gateway: ResilientLLMGateway) -> None:
        result = await gateway.generate("Hello")
        assert result.text == "Success response"
        assert gateway.request_count == 1

    @pytest.mark.asyncio
    async def test_generate_tracks_tokens(self, gateway: ResilientLLMGateway) -> None:
        await gateway.generate("Hello")
        assert gateway.total_tokens > 0

    @pytest.mark.asyncio
    async def test_unhealthy_provider_raises(self) -> None:
        provider = MockLLMProvider(healthy=False)
        gateway = ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=2, delay_seconds=[0.0, 0.0]),
        )
        with pytest.raises(LLMGenerationError, match="Failed after 2 retries"):
            await gateway.generate("Hello")

    @pytest.mark.asyncio
    async def test_content_filter_not_retried(self) -> None:
        class FilterProvider(MockLLMProvider):
            async def generate(self, prompt, params=None):
                raise LLMContentFilterError("Blocked")

        provider = FilterProvider()
        gateway = ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=3, delay_seconds=[0.0, 0.0, 0.0]),
        )
        with pytest.raises(LLMContentFilterError):
            await gateway.generate("Hello")

    @pytest.mark.asyncio
    async def test_connection_error_retried(self) -> None:
        call_count = 0

        class FlakeyProvider(MockLLMProvider):
            async def generate(self, prompt, params=None):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise LLMConnectionError("Connection refused")
                return await super().generate(prompt, params)

        provider = FlakeyProvider(responses=["Eventually works"])
        gateway = ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=3, delay_seconds=[0.0, 0.0, 0.0]),
        )
        result = await gateway.generate("Hello")
        assert result.text == "Eventually works"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_event_bus_integration(self) -> None:
        events: list[GameEvent] = []

        async def handler(event: GameEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(EventType.LLM_REQUEST_SENT, handler)
        bus.subscribe(EventType.LLM_RESPONSE_RECEIVED, handler)

        provider = MockLLMProvider(responses=["Test"])
        gateway = ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=1, delay_seconds=[0.0]),
            event_bus=bus,
        )
        await gateway.generate("Hello")
        assert len(events) == 2
        assert events[0].type == EventType.LLM_REQUEST_SENT
        assert events[1].type == EventType.LLM_RESPONSE_RECEIVED

    @pytest.mark.asyncio
    async def test_count_tokens_delegates(self, gateway: ResilientLLMGateway) -> None:
        count = gateway.count_tokens("Hello world")
        assert count >= 1

    @pytest.mark.asyncio
    async def test_is_healthy_delegates(self, gateway: ResilientLLMGateway) -> None:
        assert await gateway.is_healthy() is True

    @pytest.mark.asyncio
    async def test_close_delegates(
        self, gateway: ResilientLLMGateway, provider: MockLLMProvider
    ) -> None:
        await gateway.close()
        assert provider._closed is True

    @pytest.mark.asyncio
    async def test_retry_delay_fallback(self) -> None:
        provider = MockLLMProvider(healthy=False)
        gateway = ResilientLLMGateway(
            provider=provider,
            retry_config=RetryConfig(max_attempts=5, delay_seconds=[0.0]),
        )
        with pytest.raises(LLMGenerationError):
            await gateway.generate("Hello")
