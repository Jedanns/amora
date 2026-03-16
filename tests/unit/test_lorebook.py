import pytest

from src.lore.book import Lorebook
from src.lore.entry import LorebookCategory, LorebookEntry
from src.lore.injection import InjectionBudget


@pytest.fixture
def lorebook() -> Lorebook:
    book = Lorebook()
    book.add_entry(
        LorebookEntry(
            name="Rules",
            category=LorebookCategory.CONSTANT,
            content="These are the fundamental rules of the world.",
            priority=1000,
        )
    )
    book.add_entry(
        LorebookEntry(
            name="Tavern",
            category=LorebookCategory.LOCATION_ACTIVE,
            keys=["tavern", "auberge", "dragon ivre"],
            content="The Dragon's Drunk Tavern is the adventurer's hub.",
            priority=700,
        )
    )
    book.add_entry(
        LorebookEntry(
            name="Excalibur",
            category=LorebookCategory.CONDITIONAL,
            keys=["excalibur", "legendary sword"],
            content="Excalibur glows blue in presence of evil.",
            priority=400,
        )
    )
    book.add_entry(
        LorebookEntry(
            name="Captain Aldric",
            category=LorebookCategory.NPC_PRESENT,
            keys=["aldric", "captain"],
            content="Captain Aldric watches everything with suspicion.",
            priority=600,
        )
    )
    return book


class TestLorebook:
    def test_entry_count(self, lorebook: Lorebook) -> None:
        assert lorebook.entry_count == 4

    def test_add_and_get(self, lorebook: Lorebook) -> None:
        entry = LorebookEntry(name="New", content="New entry.")
        lorebook.add_entry(entry)
        found = lorebook.get_entry(entry.id)
        assert found is not None
        assert found.name == "New"

    def test_remove_entry(self, lorebook: Lorebook) -> None:
        entries = lorebook.list_entries()
        entry_id = entries[0].id
        assert lorebook.remove_entry(entry_id)
        assert lorebook.get_entry(entry_id) is None
        assert lorebook.entry_count == 3

    def test_remove_nonexistent(self, lorebook: Lorebook) -> None:
        assert not lorebook.remove_entry("nonexistent")

    def test_get_constant_entries(self, lorebook: Lorebook) -> None:
        constants = lorebook.get_constant_entries()
        assert len(constants) == 1
        assert constants[0].name == "Rules"

    def test_get_entries_by_category(self, lorebook: Lorebook) -> None:
        npcs = lorebook.get_entries_by_category(LorebookCategory.NPC_PRESENT)
        assert len(npcs) == 1

    def test_search_by_name(self, lorebook: Lorebook) -> None:
        results = lorebook.search_by_name("aldric")
        assert len(results) == 1

    def test_evaluate_triggers_constant(self, lorebook: Lorebook) -> None:
        results = lorebook.evaluate_triggers("any text")
        constant_triggered = [r for r in results if r.match_type == "constant"]
        assert len(constant_triggered) == 1

    def test_evaluate_triggers_keyword(self, lorebook: Lorebook) -> None:
        results = lorebook.evaluate_triggers("I enter the tavern.")
        entry_ids = {r.entry_id for r in results}
        tavern_entries = lorebook.get_entries_by_category(
            LorebookCategory.LOCATION_ACTIVE
        )
        assert any(e.id in entry_ids for e in tavern_entries)

    def test_get_triggered_entries(self, lorebook: Lorebook) -> None:
        entries = lorebook.get_triggered_entries("I look for excalibur.")
        names = {e.name for e in entries}
        assert "Excalibur" in names
        assert "Rules" in names

    def test_build_injection(self, lorebook: Lorebook) -> None:
        result = lorebook.build_injection(
            "I enter the tavern and ask about excalibur.",
            budget=InjectionBudget(max_tokens=5000),
        )
        assert result.entry_count >= 2
        text = result.to_text()
        assert "rules" in text.lower() or "Rules" in text or "fundamental" in text
        assert "Tavern" in text or "tavern" in text.lower()

    def test_build_injection_with_variables(self, lorebook: Lorebook) -> None:
        entry = LorebookEntry(
            name="Greeting",
            category=LorebookCategory.CONSTANT,
            content="Welcome {{player_name}}!",
        )
        lorebook.add_entry(entry)
        result = lorebook.build_injection(
            "hello",
            variables={"player_name": "Hero"},
        )
        assert "Hero" in result.to_text()

    def test_load_from_directory(self) -> None:
        book = Lorebook.from_directory("lore")
        assert book.entry_count > 0
        constants = book.get_constant_entries()
        assert len(constants) >= 2

    def test_export_import(self, lorebook: Lorebook) -> None:
        data = lorebook.export_entries()
        assert len(data) == 4
        new_book = Lorebook()
        count = new_book.import_entries(data)
        assert count == 4
        assert new_book.entry_count == 4
