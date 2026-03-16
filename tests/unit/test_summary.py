from __future__ import annotations

import pytest

from src.memory.summary import (
    SUMMARY_THRESHOLD_DEFAULT,
    FactType,
    KeyFact,
    Summarizer,
    Summary,
)


class TestFactType:
    def test_all_types_exist(self):
        types = list(FactType)
        assert len(types) == 8
        assert FactType.CHARACTER_RELATION in types
        assert FactType.LOCATION_VISITED in types
        assert FactType.ITEM_ACQUIRED in types
        assert FactType.QUEST_PROGRESS in types
        assert FactType.DEATH in types
        assert FactType.STATE_CHANGE in types
        assert FactType.PLAYER_DECISION in types
        assert FactType.NPC_INTERACTION in types

    def test_fact_type_values(self):
        assert FactType.CHARACTER_RELATION.value == "character_relation"
        assert FactType.DEATH.value == "death"


class TestKeyFact:
    def test_create_default(self):
        fact = KeyFact(content="Le pont est détruit")
        assert fact.content == "Le pont est détruit"
        assert fact.type == FactType.STATE_CHANGE
        assert fact.confidence == 1.0
        assert fact.id.startswith("fact_")

    def test_create_with_type(self):
        fact = KeyFact(
            type=FactType.DEATH,
            content="Le garde est mort",
            confidence=0.9,
            source_message_id="msg_123",
        )
        assert fact.type == FactType.DEATH
        assert fact.confidence == 0.9
        assert fact.source_message_id == "msg_123"

    def test_to_dict(self):
        fact = KeyFact(
            id="fact_test",
            type=FactType.ITEM_ACQUIRED,
            content="Épée obtenue",
        )
        d = fact.to_dict()
        assert d["id"] == "fact_test"
        assert d["type"] == "item_acquired"
        assert d["content"] == "Épée obtenue"
        assert "extracted_at" in d

    def test_from_dict(self):
        data = {
            "id": "fact_abc",
            "type": "location_visited",
            "content": "Taverne visitée",
            "confidence": 0.8,
            "source_message_id": "msg_1",
            "extracted_at": "2025-01-15T10:30:00+00:00",
        }
        fact = KeyFact.from_dict(data)
        assert fact.id == "fact_abc"
        assert fact.type == FactType.LOCATION_VISITED
        assert fact.content == "Taverne visitée"
        assert fact.confidence == 0.8

    def test_from_dict_defaults(self):
        fact = KeyFact.from_dict({})
        assert fact.type == FactType.STATE_CHANGE
        assert fact.content == ""
        assert fact.confidence == 1.0

    def test_frozen(self):
        fact = KeyFact(content="test")
        with pytest.raises(AttributeError):
            fact.content = "changed"  # type: ignore[misc]


class TestSummary:
    def test_create_default(self):
        summary = Summary(text="Résumé de la session")
        assert summary.text == "Résumé de la session"
        assert summary.key_facts == []
        assert summary.message_range == ("", "")
        assert summary.token_count == 0

    def test_create_with_facts(self):
        facts = [
            KeyFact(type=FactType.DEATH, content="Garde mort"),
            KeyFact(type=FactType.ITEM_ACQUIRED, content="Épée trouvée"),
        ]
        summary = Summary(
            text="Le joueur a combattu",
            key_facts=facts,
            message_range=("msg_1", "msg_50"),
            token_count=100,
        )
        assert len(summary.key_facts) == 2
        assert summary.message_range == ("msg_1", "msg_50")

    def test_to_dict(self):
        summary = Summary(
            text="Résumé",
            message_range=("a", "b"),
            token_count=50,
        )
        d = summary.to_dict()
        assert d["text"] == "Résumé"
        assert d["message_range_start"] == "a"
        assert d["message_range_end"] == "b"
        assert d["token_count"] == 50

    def test_from_dict(self):
        data = {
            "text": "Session résumée",
            "key_facts": [
                {"type": "death", "content": "PNJ mort", "confidence": 0.9}
            ],
            "message_range_start": "msg_1",
            "message_range_end": "msg_30",
            "token_count": 75,
            "created_at": "2025-01-15T10:00:00+00:00",
        }
        summary = Summary.from_dict(data)
        assert summary.text == "Session résumée"
        assert len(summary.key_facts) == 1
        assert summary.key_facts[0].type == FactType.DEATH
        assert summary.message_range == ("msg_1", "msg_30")

    def test_from_dict_defaults(self):
        summary = Summary.from_dict({})
        assert summary.text == ""
        assert summary.key_facts == []


class TestSummarizer:
    @pytest.fixture
    def summarizer(self):
        return Summarizer(summary_threshold=50, summary_every=30)

    def test_properties(self, summarizer: Summarizer):
        assert summarizer.threshold == 50
        assert summarizer.summary_interval == 30

    def test_should_summarize_below_threshold(self, summarizer: Summarizer):
        assert summarizer.should_summarize(10) is False
        assert summarizer.should_summarize(49) is False

    def test_should_summarize_at_threshold(self, summarizer: Summarizer):
        s = Summarizer(summary_threshold=50, summary_every=50)
        assert s.should_summarize(50) is True

    def test_should_summarize_at_interval(self, summarizer: Summarizer):
        assert summarizer.should_summarize(60) is True
        assert summarizer.should_summarize(90) is True
        assert summarizer.should_summarize(61) is False

    @pytest.mark.asyncio
    async def test_heuristic_summary_basic(self, summarizer: Summarizer):
        messages = [
            {"role": "user", "content": "Je vais à la taverne"},
            {"role": "assistant", "content": "Vous entrez dans la taverne. " + "A" * 100},
            {"role": "user", "content": "Je parle au tavernier"},
        ]
        summary = await summarizer.summarize(messages)
        assert isinstance(summary, Summary)
        assert summary.text != ""
        assert summary.token_count > 0

    @pytest.mark.asyncio
    async def test_heuristic_summary_with_previous(self, summarizer: Summarizer):
        messages = [
            {"role": "user", "content": "Je combat le gobelin"},
            {"role": "assistant", "content": "Le gobelin attaque ! " + "B" * 100},
        ]
        summary = await summarizer.summarize(
            messages, previous_summary="Le joueur est dans la forêt."
        )
        assert "forêt" in summary.text

    @pytest.mark.asyncio
    async def test_heuristic_summary_empty_messages(self, summarizer: Summarizer):
        summary = await summarizer.summarize([])
        assert summary.text == "Début de session."

    @pytest.mark.asyncio
    async def test_heuristic_extracts_location_facts(self, summarizer: Summarizer):
        messages = [
            {"role": "assistant", "content": "Vous arrivez à la taverne du village."},
        ]
        summary = await summarizer.summarize(messages)
        location_facts = [f for f in summary.key_facts if f.type == FactType.LOCATION_VISITED]
        assert len(location_facts) >= 1

    @pytest.mark.asyncio
    async def test_heuristic_extracts_item_facts(self, summarizer: Summarizer):
        messages = [
            {"role": "assistant", "content": "Le joueur obtient une épée magique."},
        ]
        summary = await summarizer.summarize(messages)
        item_facts = [f for f in summary.key_facts if f.type == FactType.ITEM_ACQUIRED]
        assert len(item_facts) >= 1

    @pytest.mark.asyncio
    async def test_heuristic_extracts_death_facts(self, summarizer: Summarizer):
        messages = [
            {"role": "assistant", "content": "Le garde est tué dans le combat."},
        ]
        summary = await summarizer.summarize(messages)
        death_facts = [f for f in summary.key_facts if f.type == FactType.DEATH]
        assert len(death_facts) >= 1

    @pytest.mark.asyncio
    async def test_heuristic_extracts_quest_facts(self, summarizer: Summarizer):
        messages = [
            {"role": "assistant", "content": "Nouvelle quête: retrouver l'épée perdue."},
        ]
        summary = await summarizer.summarize(messages)
        quest_facts = [f for f in summary.key_facts if f.type == FactType.QUEST_PROGRESS]
        assert len(quest_facts) >= 1

    def test_parse_facts(self, summarizer: Summarizer):
        text = (
            "[death] Le garde est mort\n"
            "[item_acquired] Épée trouvée\n"
            "[location_visited] Taverne visitée\n"
            "Invalid line\n"
            "[unknown_type] Something\n"
        )
        facts = summarizer._parse_facts(text)
        assert len(facts) == 4
        assert facts[0].type == FactType.DEATH
        assert facts[1].type == FactType.ITEM_ACQUIRED
        assert facts[2].type == FactType.LOCATION_VISITED
        assert facts[3].type == FactType.STATE_CHANGE

    def test_build_summary_prompt(self, summarizer: Summarizer):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Welcome"},
        ]
        prompt = summarizer._build_summary_prompt(messages)
        assert "Hello" in prompt
        assert "Welcome" in prompt
        assert "Résumé" in prompt

    def test_build_summary_prompt_with_previous(self, summarizer: Summarizer):
        messages = [{"role": "user", "content": "Test"}]
        prompt = summarizer._build_summary_prompt(
            messages, previous_summary="Previous context"
        )
        assert "Previous context" in prompt

    @pytest.mark.asyncio
    async def test_heuristic_includes_rolls_and_actions(self, summarizer: Summarizer):
        messages = [
            {"role": "user", "content": "Attack", "type": "action"},
            {"role": "system", "content": "Dice roll: d20 = 18", "type": "roll"},
        ]
        summary = await summarizer.summarize(messages)
        assert "Dice roll" in summary.text or "Attack" in summary.text

    def test_default_threshold(self):
        assert SUMMARY_THRESHOLD_DEFAULT == 50
