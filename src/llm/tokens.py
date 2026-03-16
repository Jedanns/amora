from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

CHARS_PER_TOKEN_RATIO = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_RATIO)


def estimate_chars_from_tokens(tokens: int) -> int:
    return tokens * CHARS_PER_TOKEN_RATIO


class TokenCounter:
    def __init__(self, use_tiktoken: bool = False, model: str = "gpt-4") -> None:
        self._use_tiktoken = use_tiktoken
        self._model = model
        self._encoder = None

        if use_tiktoken:
            try:
                import tiktoken

                self._encoder = tiktoken.encoding_for_model(model)
            except (ImportError, KeyError):
                logger.warning(
                    "tiktoken_fallback",
                    model=model,
                    reason="tiktoken unavailable or model not found, using estimation",
                )
                self._use_tiktoken = False

    def count(self, text: str) -> int:
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        return estimate_tokens(text)

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            total += 4
            for value in msg.values():
                total += self.count(value)
        total += 2
        return total

    def fits_in_budget(self, text: str, budget: int) -> bool:
        return self.count(text) <= budget

    def truncate_to_budget(self, text: str, budget: int) -> str:
        if self.fits_in_budget(text, budget):
            return text

        target_chars = estimate_chars_from_tokens(budget)
        truncated = text[:target_chars]

        if self._encoder is not None:
            while self.count(truncated) > budget and len(truncated) > 0:
                truncated = truncated[: len(truncated) - CHARS_PER_TOKEN_RATIO]

        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")
        cut_point = max(last_period, last_newline)
        if cut_point > len(truncated) // 2:
            truncated = truncated[: cut_point + 1]

        return truncated.rstrip()
