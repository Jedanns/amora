from __future__ import annotations

import pytest

from src.llm.tokens import TokenCounter
from src.lore.entry import LorebookCategory, LorebookEntry
from src.memory.context import (
    ContextBudget,
    ContextInput,
    ContextManager,
    ContextOptimizer,
    ContextResult,
    ContextSection,
)


class TestContextBudget:
    def test_calculate_default(self):
        budget = ContextBudget.calculate(max_context_tokens=12288)
        assert budget.total == 12288
        assert budget.system == 500
        assert budget.response_reserve == 512
        assert budget.available == 12288 - 512 - 500

    def test_calculate_custom(self):
        budget = ContextBudget.calculate(
            max_context_tokens=8192,
            system_tokens=200,
            response_reserve=1024,
        )
        assert budget.total == 8192
        assert budget.system == 200
        assert budget.response_reserve == 1024
        assert budget.available == 8192 - 1024 - 200

    def test_budget_ratios_sum_correctly(self):
        budget = ContextBudget.calculate(max_context_tokens=12288)
        allocated = budget.character + budget.lore + budget.history + budget.summary
        assert allocated <= budget.available

    def test_budget_zero_available(self):
        budget = ContextBudget.calculate(
            max_context_tokens=1000,
            system_tokens=500,
            response_reserve=500,
        )
        assert budget.available == 0
        assert budget.character == 0
        assert budget.lore == 0

    def test_budget_negative_clamped(self):
        budget = ContextBudget.calculate(
            max_context_tokens=1000,
            system_tokens=500,
            response_reserve=600,
        )
        assert budget.available == -100
        assert budget.character == 0
        assert budget.lore == 0


class TestContextSection:
    def test_section_creation(self):
        section = ContextSection(name="system", content="test", tokens=1)
        assert section.name == "system"
        assert section.content == "test"
        assert section.tokens == 1
        assert section.truncated is False

    def test_section_truncated(self):
        section = ContextSection(name="lore", content="test", tokens=1, truncated=True)
        assert section.truncated is True


class TestContextOptimizer:
    @pytest.fixture
    def optimizer(self):
        return ContextOptimizer(TokenCounter())

    def test_count_tokens_caching(self, optimizer: ContextOptimizer):
        text = "Hello world"
        t1 = optimizer.count_tokens(text)
        t2 = optimizer.count_tokens(text)
        assert t1 == t2
        assert t1 > 0

    def test_select_lore_entries_within_budget(self, optimizer: ContextOptimizer):
        entries = [
            LorebookEntry(
                name="Entry1",
                content="Short",
                priority=800,
                category=LorebookCategory.QUEST_STATE,
            ),
            LorebookEntry(
                name="Entry2",
                content="Another entry",
                priority=600,
                category=LorebookCategory.NPC_PRESENT,
            ),
        ]
        selected, tokens = optimizer.select_lore_entries(entries, budget=1000)
        assert len(selected) == 2
        assert tokens > 0

    def test_select_lore_entries_budget_limit(self, optimizer: ContextOptimizer):
        entries = [
            LorebookEntry(
                name="Entry1",
                content="A" * 400,
                priority=800,
                category=LorebookCategory.QUEST_STATE,
            ),
            LorebookEntry(
                name="Entry2",
                content="B" * 400,
                priority=600,
                category=LorebookCategory.NPC_PRESENT,
            ),
        ]
        selected, _tokens = optimizer.select_lore_entries(entries, budget=110)
        assert len(selected) == 1
        assert selected[0].priority == 800

    def test_select_lore_constant_first(self, optimizer: ContextOptimizer):
        entries = [
            LorebookEntry(
                name="Ambient",
                content="Background",
                priority=200,
                category=LorebookCategory.AMBIENT,
            ),
            LorebookEntry(
                name="Rule",
                content="Core rule",
                priority=1000,
                category=LorebookCategory.CONSTANT,
            ),
        ]
        selected, _ = optimizer.select_lore_entries(entries, budget=50)
        assert selected[0].category == LorebookCategory.CONSTANT

    def test_select_history_most_recent(self, optimizer: ContextOptimizer):
        messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(20)
        ]
        selected, _tokens = optimizer.select_history(messages, budget=100)
        assert len(selected) > 0
        assert len(selected) < 20
        assert selected[-1]["content"] == "Message 19"

    def test_select_history_all_fit(self, optimizer: ContextOptimizer):
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        selected, _ = optimizer.select_history(messages, budget=1000)
        assert len(selected) == 2

    def test_clear_cache(self, optimizer: ContextOptimizer):
        optimizer.count_tokens("test")
        assert len(optimizer._token_cache) > 0
        optimizer.clear_cache()
        assert len(optimizer._token_cache) == 0


class TestContextManager:
    @pytest.fixture
    def manager(self):
        return ContextManager(max_context_tokens=4096, max_response_tokens=256)

    def test_properties(self, manager: ContextManager):
        assert manager.max_context_tokens == 4096
        assert manager.max_response_tokens == 256

    def test_build_minimal(self, manager: ContextManager):
        ctx_input = ContextInput(user_input="Hello")
        result = manager.build(ctx_input)
        assert isinstance(result, ContextResult)
        assert "<|im_start|>user\nHello<|im_end|>" in result.prompt
        assert "Hello" in result.prompt
        assert result.total_tokens > 0

    def test_build_with_system_prompt(self, manager: ContextManager):
        ctx_input = ContextInput(
            user_input="Hello",
            system_prompt="You are a narrator.",
        )
        result = manager.build(ctx_input)
        assert "[INSTRUCTIONS]" in result.prompt
        assert "narrator" in result.prompt

    def test_build_with_lore(self, manager: ContextManager):
        entries = [
            LorebookEntry(
                name="Tavern",
                content="La Taverne du Vieux Greg est un lieu mystérieux.",
                priority=700,
                category=LorebookCategory.LOCATION_ACTIVE,
            ),
        ]
        ctx_input = ContextInput(
            user_input="Je suis dans la taverne",
            lore_entries=entries,
        )
        result = manager.build(ctx_input)
        assert "[CONTEXTE DU MONDE]" in result.prompt
        assert "Taverne" in result.prompt
        assert result.lore_entries_included == 1

    def test_build_with_history(self, manager: ContextManager):
        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bienvenue aventurier !"},
        ]
        ctx_input = ContextInput(
            user_input="Que faire ?",
            conversation_history=history,
        )
        result = manager.build(ctx_input)
        assert "<|im_start|>user\nBonjour<|im_end|>" in result.prompt
        assert "Bonjour" in result.prompt
        assert result.history_messages_included == 2

    def test_build_with_summary(self, manager: ContextManager):
        ctx_input = ContextInput(
            user_input="Continue",
            summary_text="Le joueur a exploré la forêt et trouvé un coffre.",
            key_facts=["Coffre trouvé dans la forêt"],
        )
        result = manager.build(ctx_input)
        assert "[RÉSUMÉ]" in result.prompt
        assert "forêt" in result.prompt
        assert "Faits importants" in result.prompt
        assert result.summary_included is True

    def test_build_with_extra_context(self, manager: ContextManager):
        ctx_input = ContextInput(
            user_input="Attack",
            extra_context="Combat actif: Gobelin (HP: 15/20)",
        )
        result = manager.build(ctx_input)
        assert "Gobelin" in result.prompt

    def test_budget_tracking(self, manager: ContextManager):
        ctx_input = ContextInput(user_input="Test")
        result = manager.build(ctx_input)
        assert result.budget.total == 4096
        assert result.budget.response_reserve == 256
        assert result.budget_remaining >= 0
        assert result.budget_used > 0

    def test_truncation_flag_on_overflow(self):
        small_manager = ContextManager(max_context_tokens=800, max_response_tokens=50)
        entries = [
            LorebookEntry(
                name=f"Entry{i}",
                content="A" * 200,
                priority=800 - i * 100,
                category=LorebookCategory.QUEST_STATE,
            )
            for i in range(5)
        ]
        ctx_input = ContextInput(
            user_input="Test",
            lore_entries=entries,
        )
        result = small_manager.build(ctx_input)
        assert result.truncated is True
        assert result.lore_entries_included < 5

    def test_prompt_section_order(self, manager: ContextManager):
        ctx_input = ContextInput(
            user_input="Test",
            system_prompt="System prompt",
            summary_text="Summary text",
            conversation_history=[{"role": "user", "content": "Previous"}],
            lore_entries=[
                LorebookEntry(
                    name="Lore",
                    content="Lore content",
                    priority=700,
                    category=LorebookCategory.LOCATION_ACTIVE,
                ),
            ],
        )
        result = manager.build(ctx_input)
        system_pos = result.prompt.find("[INSTRUCTIONS]")
        summary_pos = result.prompt.find("[RÉSUMÉ]")
        lore_pos = result.prompt.find("[CONTEXTE DU MONDE]")
        history_pos = result.prompt.find("Previous")
        user_pos = result.prompt.find("<|im_start|>user\nTest<|im_end|>")

        assert system_pos < summary_pos < lore_pos < history_pos < user_pos

    def test_estimate_remaining_budget(self, manager: ContextManager):
        remaining = manager.estimate_remaining_budget(system_prompt="Short prompt")
        assert remaining > 0
        assert remaining < 4096

    def test_history_chronological_order(self, manager: ContextManager):
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]
        ctx_input = ContextInput(
            user_input="Fourth",
            conversation_history=history,
        )
        result = manager.build(ctx_input)
        first_pos = result.prompt.find("First")
        second_pos = result.prompt.find("Second")
        third_pos = result.prompt.find("Third")
        assert first_pos < second_pos < third_pos

    def test_empty_sections_not_included(self, manager: ContextManager):
        ctx_input = ContextInput(user_input="Only user")
        result = manager.build(ctx_input)
        assert "[INSTRUCTIONS]" not in result.prompt
        assert "[CONTEXTE DU MONDE]" not in result.prompt
        assert "[RÉSUMÉ]" not in result.prompt
        assert "<|im_start|>user\nOnly user<|im_end|>" in result.prompt

    def test_key_facts_only(self, manager: ContextManager):
        ctx_input = ContextInput(
            user_input="Test",
            key_facts=["Le pont est détruit", "Le garde est mort"],
        )
        result = manager.build(ctx_input)
        assert "pont est détruit" in result.prompt
        assert "garde est mort" in result.prompt
        assert result.summary_included is True

    def test_context_result_properties(self, manager: ContextManager):
        ctx_input = ContextInput(user_input="Test")
        result = manager.build(ctx_input)
        assert result.budget_used == result.total_tokens
        assert result.budget_remaining == (
            result.budget.total - result.budget.response_reserve - result.total_tokens
        )


class TestContextInput:
    def test_default_values(self):
        ctx = ContextInput(user_input="test")
        assert ctx.user_input == "test"
        assert ctx.system_prompt == ""
        assert ctx.character is None
        assert ctx.lore_entries == []
        assert ctx.conversation_history == []
        assert ctx.summary_text == ""
        assert ctx.key_facts == []
        assert ctx.extra_context == ""
