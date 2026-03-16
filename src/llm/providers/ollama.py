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

OLLAMA_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_TAGS_ENDPOINT = "/api/tags"


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._model = model
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
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "top_k": params.top_k,
            },
        }
        if params.stop_sequences:
            payload["options"]["stop"] = params.stop_sequences

        start_time = time.monotonic()

        try:
            async with session.post(
                f"{self._url}{OLLAMA_GENERATE_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"Ollama returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )
                data = await resp.json()

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self._url}",
                context={"url": self._url, "error": str(exc)},
            ) from exc

        duration = time.monotonic() - start_time
        text = data.get("response", "")
        eval_count = data.get("eval_count", estimate_tokens(text))
        prompt_eval_count = data.get("prompt_eval_count", estimate_tokens(prompt))
        model = data.get("model", self._model)

        return GenerationResult(
            text=text,
            tokens_generated=eval_count,
            tokens_prompt=prompt_eval_count,
            duration_seconds=duration,
            model=model,
            finish_reason="stop" if data.get("done", False) else "length",
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
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "top_k": params.top_k,
            },
        }
        if params.stop_sequences:
            payload["options"]["stop"] = params.stop_sequences

        try:
            async with session.post(
                f"{self._url}{OLLAMA_GENERATE_ENDPOINT}",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMGenerationError(
                        f"Ollama stream returned status {resp.status}",
                        context={"status": resp.status, "body": body},
                    )

                import json

                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if not decoded:
                        continue
                    chunk_data = json.loads(decoded)
                    token = chunk_data.get("response", "")
                    if token:
                        yield token
                    if chunk_data.get("done", False):
                        break

        except aiohttp.ClientError as exc:
            raise LLMConnectionError(
                "Ollama stream connection failed",
                context={"url": self._url, "error": str(exc)},
            ) from exc

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def is_healthy(self) -> bool:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{OLLAMA_TAGS_ENDPOINT}",
            ) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, TimeoutError, OSError):
            return False

    async def get_model_info(self) -> dict[str, Any]:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._url}{OLLAMA_TAGS_ENDPOINT}",
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    names = [m.get("name", "") for m in models]
                    return {
                        "model": self._model,
                        "available_models": names,
                        "provider": "ollama",
                    }
                return {"model": self._model, "provider": "ollama"}
        except (aiohttp.ClientError, TimeoutError, OSError):
            return {"model": self._model, "provider": "ollama", "error": "unreachable"}

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
