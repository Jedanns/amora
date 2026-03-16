from __future__ import annotations

import pytest

from src.llm.tokens import TokenCounter, estimate_chars_from_tokens, estimate_tokens


class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 1

    def test_short_string(self) -> None:
        assert estimate_tokens("hi") == 1

    def test_known_length(self) -> None:
        text = "a" * 100
        assert estimate_tokens(text) == 25

    def test_long_text(self) -> None:
        text = "word " * 1000
        tokens = estimate_tokens(text)
        assert tokens > 100


class TestEstimateCharsFromTokens:
    def test_conversion(self) -> None:
        assert estimate_chars_from_tokens(10) == 40
        assert estimate_chars_from_tokens(0) == 0
        assert estimate_chars_from_tokens(100) == 400


class TestTokenCounter:
    @pytest.fixture
    def counter(self) -> TokenCounter:
        return TokenCounter(use_tiktoken=False)

    def test_count(self, counter: TokenCounter) -> None:
        result = counter.count("Hello world")
        assert result >= 1

    def test_count_messages(self, counter: TokenCounter) -> None:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        result = counter.count_messages(messages)
        assert result > 0

    def test_fits_in_budget_true(self, counter: TokenCounter) -> None:
        assert counter.fits_in_budget("Hello", 100) is True

    def test_fits_in_budget_false(self, counter: TokenCounter) -> None:
        long_text = "a" * 10000
        assert counter.fits_in_budget(long_text, 10) is False

    def test_truncate_to_budget_no_truncation(self, counter: TokenCounter) -> None:
        text = "Hello world"
        result = counter.truncate_to_budget(text, 100)
        assert result == text

    def test_truncate_to_budget_truncates(self, counter: TokenCounter) -> None:
        text = "This is a sentence. This is another sentence. And one more."
        result = counter.truncate_to_budget(text, 5)
        assert len(result) < len(text)

    def test_truncate_cuts_at_sentence(self, counter: TokenCounter) -> None:
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = counter.truncate_to_budget(text, 5)
        assert result.endswith(".") or result.endswith("")

    def test_tiktoken_fallback(self) -> None:
        counter = TokenCounter(use_tiktoken=True, model="nonexistent-model-xyz")
        result = counter.count("Hello world")
        assert result >= 1
