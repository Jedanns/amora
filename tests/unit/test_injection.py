from src.lore.entry import LorebookCategory, LorebookEntry
from src.lore.injection import (
    InjectionBudget,
    InjectionPipeline,
    estimate_tokens,
)


class TestEstimateTokens:
    def test_basic(self) -> None:
        tokens = estimate_tokens("Hello world!")
        assert tokens > 0

    def test_empty(self) -> None:
        tokens = estimate_tokens("")
        assert tokens >= 1

    def test_long_text(self) -> None:
        text = "word " * 1000
        tokens = estimate_tokens(text)
        assert tokens > 100


class TestInjectionBudget:
    def test_default_budget(self) -> None:
        budget = InjectionBudget()
        assert budget.available > 0
        assert budget.available == 16384 - 512 - 200

    def test_custom_budget(self) -> None:
        budget = InjectionBudget(
            max_tokens=8192,
            reserve_response=1024,
            system_prompt_tokens=500,
            history_tokens=2000,
        )
        assert budget.available == 8192 - 1024 - 500 - 2000

    def test_budget_cannot_be_negative(self) -> None:
        budget = InjectionBudget(
            max_tokens=100,
            reserve_response=200,
        )
        assert budget.available == 0


class TestInjectionPipeline:
    def _make_entry(
        self,
        name: str = "Test",
        content: str = "Short content.",
        priority: int = 500,
        order: int = 100,
        category: LorebookCategory = LorebookCategory.CONDITIONAL,
    ) -> LorebookEntry:
        return LorebookEntry(
            name=name,
            content=content,
            priority=priority,
            order=order,
            category=category,
        )

    def test_inject_single_entry(self) -> None:
        pipeline = InjectionPipeline(budget=InjectionBudget(max_tokens=1000))
        entries = [self._make_entry(content="Test content for injection.")]
        result = pipeline.inject(entries)
        assert result.entry_count == 1
        assert result.total_tokens > 0
        assert "Test content" in result.to_text()

    def test_priority_ordering(self) -> None:
        pipeline = InjectionPipeline(budget=InjectionBudget(max_tokens=5000))
        entries = [
            self._make_entry(name="Low", content="Low priority.", priority=200),
            self._make_entry(name="High", content="High priority.", priority=900),
            self._make_entry(name="Mid", content="Mid priority.", priority=500),
        ]
        result = pipeline.inject(entries)
        assert result.entry_count == 3
        text = result.to_text()
        high_pos = text.index("High priority")
        low_pos = text.index("Low priority")
        assert high_pos < low_pos

    def test_budget_limit_drops_low_priority(self) -> None:
        pipeline = InjectionPipeline(
            budget=InjectionBudget(
                max_tokens=100,
                reserve_response=0,
                system_prompt_tokens=0,
            )
        )
        entries = [
            self._make_entry(name="Important", content="A" * 500, priority=900),
            self._make_entry(name="Less", content="B" * 500, priority=100),
        ]
        result = pipeline.inject(entries)
        assert result.entry_count <= 1
        assert len(result.dropped_entries) >= 1

    def test_deduplication(self) -> None:
        pipeline = InjectionPipeline(budget=InjectionBudget(max_tokens=5000))
        entry = self._make_entry(content="Duplicate entry.")
        result = pipeline.inject([entry, entry, entry])
        assert result.entry_count == 1

    def test_variable_substitution(self) -> None:
        pipeline = InjectionPipeline(
            budget=InjectionBudget(max_tokens=5000),
            variables={"player_name": "Aldric"},
        )
        entry = self._make_entry(content="Welcome {{player_name}}!")
        result = pipeline.inject([entry])
        assert "Aldric" in result.to_text()
        assert "{{" not in result.to_text()

    def test_empty_entries(self) -> None:
        pipeline = InjectionPipeline()
        result = pipeline.inject([])
        assert result.entry_count == 0
        assert result.total_tokens == 0
        assert result.to_text() == ""

    def test_truncatable_entry(self) -> None:
        pipeline = InjectionPipeline(
            budget=InjectionBudget(
                max_tokens=50,
                reserve_response=0,
                system_prompt_tokens=0,
            )
        )
        long_content = "This is a long sentence. " * 20
        entry = self._make_entry(
            content=long_content,
            priority=500,
        )
        entry.truncatable = True
        entry.min_tokens = 10
        result = pipeline.inject([entry])
        assert result.entry_count == 1
        assert result.entries[0].truncated

    def test_set_variables(self) -> None:
        pipeline = InjectionPipeline()
        pipeline.set_variables({"location": "Valcrest"})
        entry = self._make_entry(content="You are in {{location}}.")
        result = pipeline.inject([entry])
        assert "Valcrest" in result.to_text()
