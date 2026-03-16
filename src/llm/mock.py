from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.llm.gateway import GenerationParams, GenerationResult, LLMProvider
from src.llm.tokens import estimate_tokens

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class MockLLMProvider(LLMProvider):
    def __init__(
        self,
        responses: list[str] | None = None,
        healthy: bool = True,
        latency: float = 0.0,
        model_name: str = "mock-model",
    ) -> None:
        self._responses = list(responses) if responses else ["Mock response."]
        self._healthy = healthy
        self._latency = latency
        self._model_name = model_name
        self._call_count = 0
        self._prompts: list[str] = []
        self._closed = False

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def prompts(self) -> list[str]:
        return list(self._prompts)

    @property
    def last_prompt(self) -> str | None:
        return self._prompts[-1] if self._prompts else None

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    def set_responses(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> GenerationResult:
        if self._latency > 0:
            import asyncio

            await asyncio.sleep(self._latency)

        self._prompts.append(prompt)
        idx = self._call_count % len(self._responses)
        text = self._responses[idx]
        self._call_count += 1

        return GenerationResult(
            text=text,
            tokens_generated=estimate_tokens(text),
            tokens_prompt=estimate_tokens(prompt),
            duration_seconds=self._latency or 0.01,
            model=self._model_name,
            finish_reason="stop",
        )

    async def generate_stream(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> AsyncIterator[str]:
        if self._latency > 0:
            import asyncio

            await asyncio.sleep(self._latency)

        self._prompts.append(prompt)
        idx = self._call_count % len(self._responses)
        text = self._responses[idx]
        self._call_count += 1

        for word in text.split(" "):
            yield word + " "

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def is_healthy(self) -> bool:
        return self._healthy

    async def get_model_info(self) -> dict[str, Any]:
        return {"model": self._model_name, "provider": "mock"}

    async def close(self) -> None:
        self._closed = True
