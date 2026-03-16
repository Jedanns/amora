from src.lore.entry import (
    CATEGORY_DEFAULTS,
    LorebookCategory,
    LorebookEntry,
)


class TestLorebookEntry:
    def test_creation(self) -> None:
        entry = LorebookEntry(
            name="Test Entry",
            category=LorebookCategory.CONDITIONAL,
            keys=["test", "example"],
            content="This is test content.",
        )
        assert entry.name == "Test Entry"
        assert entry.category == LorebookCategory.CONDITIONAL
        assert len(entry.keys) == 2
        assert entry.has_keys

    def test_constant_entry(self) -> None:
        entry = LorebookEntry(
            name="Rules",
            category=LorebookCategory.CONSTANT,
            content="Always injected.",
        )
        assert entry.is_constant
        assert not entry.has_keys

    def test_apply_category_defaults(self) -> None:
        entry = LorebookEntry(name="NPC", category=LorebookCategory.NPC_PRESENT)
        entry.apply_category_defaults()
        defaults = CATEGORY_DEFAULTS[LorebookCategory.NPC_PRESENT]
        assert entry.priority == defaults["priority"]
        assert entry.scan_depth == defaults["scan_depth"]
        assert entry.trigger_chance == defaults["trigger_chance"]

    def test_effective_priority_with_boost(self) -> None:
        entry = LorebookEntry(name="Test", priority=800)
        assert entry.effective_priority(boost=100) == 900
        assert entry.effective_priority(boost=300) == 1000

    def test_to_injection_text(self) -> None:
        entry = LorebookEntry(
            name="Test",
            content="Hello {{player_name}}, welcome to {{location}}!",
        )
        text = entry.to_injection_text(
            {"player_name": "Aldric", "location": "Valcrest"}
        )
        assert "Aldric" in text
        assert "Valcrest" in text
        assert "{{" not in text

    def test_to_injection_text_no_variables(self) -> None:
        entry = LorebookEntry(name="Test", content="No variables here.")
        text = entry.to_injection_text()
        assert text == "No variables here."

    def test_disabled_entry(self) -> None:
        entry = LorebookEntry(name="Disabled", enabled=False)
        assert not entry.enabled

    def test_id_auto_generated(self) -> None:
        e1 = LorebookEntry(name="A")
        e2 = LorebookEntry(name="B")
        assert e1.id != e2.id
        assert e1.id.startswith("lore_")
