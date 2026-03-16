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

LMSTUDIO_COMPLETIONS_ENDPOINT = "/v1/completions"
LMSTUDIO_MODELS_ENDPOINT = "/v1/models"


class LMStudioProvider(LLMProvider):
    def __init__(
        self,
        url: str = "http://localhost:1234",
        timeout: float = 120.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._model: str = "local-model"

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
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "stream": False,
        }
        if params.stop_sequences:
            payload["stop"] = params.stop_sequences

        start_time = time.monotonic()

        try:
            async with session.post(
                f"{self._url}{LMSTUDIO_COMPLETIONS_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"LM Studio returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )
                data = await resp.json()

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                f"Failed to connect to LM Studio at {self._url}",
                context={"url": self._url, "error": str(exc)},
            ) from exc

        duration = time.monotonic() - start_time
        choices = data.get("choices", [])
        if not choices:
            raise LLMGenerationError(
                "LM Studio returned empty choices",
                context={"response": data},
            )

        text = choices[0].get("text", "")
        usage = data.get("usage", {})
        tokens_generated = usage.get("completion_tokens", estimate_tokens(text))
        tokens_prompt = usage.get("prompt_tokens", estimate_tokens(prompt))
        model = data.get("model", self._model)

        return GenerationResult(
            text=text,
            tokens_generated=tokens_generated,
            tokens_prompt=tokens_prompt,
            duration_seconds=duration,
            model=model,
            finish_reason=choices[0].get("finish_reason", "stop"),
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
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "stream": True,
        }
        if params.stop_sequences:
            payload["stop"] = params.stop_sequences

        try:
            async with session.post(
                f"{self._url}{LMSTUDIO_COMPLETIONS_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"LM Studio stream returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )

                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data:"):
                        chunk_str = decoded[5:].strip()
                        if chunk_str == "[DONE]":
                            break
                        import json

                        chunk_data = json.loads(chunk_str)
                        choices = chunk_data.get("choices", [])
                        if choices:
                            text = choices[0].get("text", "")
                            if text:
                                yield text

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                "LM Studio stream connection failed",
                context={"url": self._url, "error": str(exc)},
            ) from exc

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def is_healthy(self) -> bool:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{LMSTUDIO_MODELS_ENDPOINT}",
            ) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, TimeoutError, OSError):
            return False

    async def get_model_info(self) -> dict[str, Any]:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{LMSTUDIO_MODELS_ENDPOINT}",
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("data", [])
                    if models:
                        return {
                            "model": models[0].get("id", "unknown"),
                            "provider": "lmstudio",
                        }
                return {"model": "unknown", "provider": "lmstudio"}
        except (aiohttp.ClientError, TimeoutError, OSError):
            return {"model": "unknown", "provider": "lmstudio", "error": "unreachable"}

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
