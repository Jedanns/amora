from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import aiohttp
import structlog

from src.core.exceptions import LLMConnectionError, LLMGenerationError
from src.llm.gateway import GenerationParams, GenerationResult, LLMProvider
from src.llm.tokens import estimate_tokens

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)

KOBOLDCPP_GENERATE_ENDPOINT = "/api/v1/generate"
KOBOLDCPP_MODEL_ENDPOINT = "/api/v1/model"
KOBOLDCPP_STREAM_ENDPOINT = "/api/extra/generate/stream"
KOBOLDCPP_TOKEN_COUNT_ENDPOINT = "/api/extra/tokencount"


class KoboldCPPProvider(LLMProvider):
    def __init__(
        self,
        url: str = "http://localhost:5001",
        timeout: float = 120.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> GenerationResult:
        params = params or GenerationParams()
        session = await self._get_session()

        payload: dict[str, Any] = {
            "prompt": prompt,
            "max_length": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "top_k": params.top_k,
        }
        if params.stop_sequences:
            payload["stop_sequence"] = params.stop_sequences

        start_time = time.monotonic()

        try:
            async with session.post(
                f"{self._url}{KOBOLDCPP_GENERATE_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"KoboldCPP returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )

                data = await resp.json()

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                f"Failed to connect to KoboldCPP at {self._url}",
                context={"url": self._url, "error": str(exc)},
            ) from exc

        duration = time.monotonic() - start_time
        results = data.get("results", [])
        if not results:
            raise LLMGenerationError(
                "KoboldCPP returned empty results",
                context={"response": data},
            )

        text = results[0].get("text", "")
        tokens_generated = estimate_tokens(text)

        return GenerationResult(
            text=text,
            tokens_generated=tokens_generated,
            tokens_prompt=estimate_tokens(prompt),
            duration_seconds=duration,
            finish_reason="stop",
            raw_response=data,
        )

    async def generate_stream(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> AsyncIterator[str]:
        params = params or GenerationParams()
        session = await self._get_session()

        payload: dict[str, Any] = {
            "prompt": prompt,
            "max_length": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "top_k": params.top_k,
        }
        if params.stop_sequences:
            payload["stop_sequence"] = params.stop_sequences

        try:
            async with session.post(
                f"{self._url}{KOBOLDCPP_STREAM_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"KoboldCPP stream returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )

                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data:"):
                        import json

                        chunk_data = json.loads(decoded[5:].strip())
                        token = chunk_data.get("token", "")
                        if token:
                            yield token

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                "KoboldCPP stream connection failed",
                context={"url": self._url, "error": str(exc)},
            ) from exc

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def count_tokens_api(self, text: str) -> int:
        session = await self._get_session()
        try:
            async with session.post(
                f"{self._url}{KOBOLDCPP_TOKEN_COUNT_ENDPOINT}",
                json={"prompt": text},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("value", estimate_tokens(text))
                return estimate_tokens(text)
        except aiohttp.ClientError:
            return estimate_tokens(text)

    async def is_healthy(self) -> bool:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{KOBOLDCPP_MODEL_ENDPOINT}",
            ) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, TimeoutError, OSError):
            return False

    async def get_model_info(self) -> dict[str, Any]:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{KOBOLDCPP_MODEL_ENDPOINT}",
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "model": data.get("result", "unknown"),
                        "provider": "koboldcpp",
                    }
                return {"model": "unknown", "provider": "koboldcpp"}
        except (aiohttp.ClientError, TimeoutError, OSError):
            return {"model": "unknown", "provider": "koboldcpp", "error": "unreachable"}

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
