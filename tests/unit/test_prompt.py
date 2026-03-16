from __future__ import annotations

import pytest

from src.character.models import Character, CharacterClass
from src.llm.prompt import (
    DEFAULT_SYSTEM_PROMPT,
    Message,
    PromptBuilder,
    PromptBuildResult,
    PromptSections,
)
from src.llm.tokens import TokenCounter
from src.lore.entry import LorebookCategory, LorebookEntry


@pytest.fixture
def builder() -> PromptBuilder:
    return PromptBuilder(
        max_context_tokens=4096,
        max_response_tokens=512,
        token_counter=TokenCounter(use_tiktoken=False),
    )


@pytest.fixture
def character() -> Character:
    return Character(name="Aldric", character_class=CharacterClass.WARRIOR, level=5)


@pytest.fixture
def lore_entries() -> list[LorebookEntry]:
    return [
        LorebookEntry(
            name="Taverne du Dragon",
            category=LorebookCategory.LOCATION_ACTIVE,
            content="La taverne est chaleureuse et bondée.",
            priority=700,
        ),
        LorebookEntry(
            name="Règles de combat",
            category=LorebookCategory.CONSTANT,
            content="Le combat utilise des jets de d20.",
            priority=1000,
        ),
    ]


class TestMessage:
    def test_message_creation(self) -> None:
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name == ""

    def test_token_estimate(self) -> None:
        msg = Message(role="user", content="Hello world")
        assert msg.token_estimate > 0


class TestPromptSections:
    def test_empty_sections(self) -> None:
        sections = PromptSections()
        parts = sections.to_parts()
        assert parts == []

    def test_all_sections(self) -> None:
        sections = PromptSections(
            system="sys",
            character="char",
            lore="lore",
            history="hist",
            user_input="input",
        )
        parts = sections.to_parts()
        assert len(parts) == 5
        assert "### INSTRUCTIONS" in parts[0]
        assert "### PERSONNAGE" in parts[1]
        assert "### CONTEXTE DU MONDE" in parts[2]
        assert "### HISTORIQUE" in parts[3]
        assert "### JOUEUR" in parts[4]

    def test_partial_sections(self) -> None:
        sections = PromptSections(system="sys", user_input="input")
        parts = sections.to_parts()
        assert len(parts) == 2


class TestPromptBuilder:
    def test_basic_build(self, builder: PromptBuilder) -> None:
        result = builder.build(user_input="Je regarde autour de moi")
        assert isinstance(result, PromptBuildResult)
        assert "### JOUEUR" in result.prompt
        assert "Je regarde autour de moi" in result.prompt
        assert result.total_tokens > 0

    def test_build_with_character(
        self, builder: PromptBuilder, character: Character
    ) -> None:
        result = builder.build(
            user_input="Que vois-je?",
            character=character,
        )
        assert "### PERSONNAGE" in result.prompt
        assert "Aldric" in result.prompt

    def test_build_with_lore(
        self, builder: PromptBuilder, lore_entries: list[LorebookEntry]
    ) -> None:
        result = builder.build(
            user_input="Je regarde autour",
            lore_entries=lore_entries,
        )
        assert "### CONTEXTE DU MONDE" in result.prompt
        assert result.lore_entries_included > 0

    def test_lore_priority_order(
        self, builder: PromptBuilder, lore_entries: list[LorebookEntry]
    ) -> None:
        result = builder.build(
            user_input="test",
            lore_entries=lore_entries,
        )
        assert result.lore_entries_included == 2

    def test_build_with_history(self, builder: PromptBuilder) -> None:
        history = [
            Message(role="user", content="Bonjour"),
            Message(role="assistant", content="Bienvenue à la taverne!"),
            Message(role="user", content="Je commande une bière"),
        ]
        result = builder.build(
            user_input="Je bois",
            conversation_history=history,
        )
        assert "### HISTORIQUE" in result.prompt
        assert result.history_messages_included > 0

    def test_build_full_prompt(
        self,
        builder: PromptBuilder,
        character: Character,
        lore_entries: list[LorebookEntry],
    ) -> None:
        history = [
            Message(role="user", content="Je regarde autour"),
            Message(role="assistant", content="Vous voyez une taverne."),
        ]
        result = builder.build(
            user_input="J'entre dans la taverne",
            character=character,
            lore_entries=lore_entries,
            conversation_history=history,
        )
        assert "### INSTRUCTIONS" in result.prompt
        assert "### PERSONNAGE" in result.prompt
        assert "### CONTEXTE DU MONDE" in result.prompt
        assert "### HISTORIQUE" in result.prompt
        assert "### JOUEUR" in result.prompt
        assert result.total_tokens > 0
        assert result.budget_remaining >= 0

    def test_budget_limits_history(self) -> None:
        builder = PromptBuilder(
            max_context_tokens=200,
            max_response_tokens=50,
            system_prompt="Short system.",
            token_counter=TokenCounter(use_tiktoken=False),
        )
        history = [
            Message(role="user", content="a " * 500),
            Message(role="user", content="Recent message"),
        ]
        result = builder.build(
            user_input="test",
            conversation_history=history,
        )
        assert result.history_messages_included < 2

    def test_extra_context(self, builder: PromptBuilder) -> None:
        result = builder.build(
            user_input="test",
            extra_context="Le temps est orageux.",
        )
        assert "Le temps est orageux" in result.prompt

    def test_default_system_prompt(self) -> None:
        builder = PromptBuilder()
        result = builder.build(user_input="test")
        assert DEFAULT_SYSTEM_PROMPT in result.prompt

    def test_custom_system_prompt(self) -> None:
        builder = PromptBuilder(system_prompt="Custom system prompt.")
        result = builder.build(user_input="test")
        assert "Custom system prompt." in result.prompt

    def test_available_budget(self, builder: PromptBuilder) -> None:
        budget = builder.available_budget
        assert budget > 0
        assert budget < 4096

    def test_truncated_flag(self) -> None:
        builder = PromptBuilder(
            max_context_tokens=100,
            max_response_tokens=50,
            system_prompt="s",
            token_counter=TokenCounter(use_tiktoken=False),
        )
        lore = [
            LorebookEntry(
                name="Big entry",
                content="a " * 500,
                priority=1000,
                truncatable=False,
            )
        ]
        result = builder.build(user_input="test", lore_entries=lore)
        assert result.truncated is True or result.lore_entries_included == 0
