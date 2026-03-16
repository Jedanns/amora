import pytest

from src.memory.retrieval import LoreRetriever


class TestLoreRetriever:
    @pytest.fixture
    def retriever(self) -> LoreRetriever:
        r = LoreRetriever(collection_name="test_lore")
        r.initialize()
        return r

    def test_initialize(self, retriever: LoreRetriever) -> None:
        assert retriever.is_available

    def test_index_entries(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "lore_001",
                "name": "Tavern",
                "content": "The Dragon's Drunk Tavern is a popular gathering place for adventurers.",
                "category": "location",
                "priority": 700,
            },
            {
                "id": "lore_002",
                "name": "Excalibur",
                "content": "Excalibur is a legendary sword that glows blue near evil creatures.",
                "category": "item",
                "priority": 400,
            },
            {
                "id": "lore_003",
                "name": "Forest",
                "content": "The Dark Forest is filled with dangerous monsters and ancient ruins.",
                "category": "location",
                "priority": 500,
            },
        ]
        count = retriever.index_entries(entries)
        assert count == 3
        assert retriever.indexed_count == 3

    def test_search(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "lore_001",
                "name": "Tavern",
                "content": "The tavern serves the best beer in the kingdom.",
                "category": "location",
                "priority": 700,
            },
            {
                "id": "lore_002",
                "name": "Sword",
                "content": "The legendary sword was forged by ancient elves.",
                "category": "item",
                "priority": 400,
            },
        ]
        retriever.index_entries(entries)
        results = retriever.search("Where can I get a drink?", n_results=5)
        assert len(results) > 0
        assert results[0].entry_id in ["lore_001", "lore_002"]

    def test_search_empty_index(self, retriever: LoreRetriever) -> None:
        results = retriever.search("test query")
        assert len(results) == 0

    def test_search_with_category_filter(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "loc_001",
                "name": "Tavern",
                "content": "A warm tavern.",
                "category": "location",
                "priority": 700,
            },
            {
                "id": "item_001",
                "name": "Sword",
                "content": "A sharp sword.",
                "category": "item",
                "priority": 400,
            },
        ]
        retriever.index_entries(entries)
        results = retriever.search("tavern sword", category_filter="location")
        ids = {r.entry_id for r in results}
        assert "loc_001" in ids

    def test_clear(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "lore_001",
                "name": "Test",
                "content": "Test content.",
                "category": "test",
                "priority": 100,
            },
        ]
        retriever.index_entries(entries)
        assert retriever.indexed_count == 1
        retriever.clear()
        assert retriever.indexed_count == 0

    def test_index_skips_empty(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "",
                "name": "No ID",
                "content": "Content",
                "category": "test",
                "priority": 100,
            },
            {
                "id": "valid",
                "name": "Valid",
                "content": "",
                "category": "test",
                "priority": 100,
            },
            {
                "id": "ok",
                "name": "OK",
                "content": "Real content",
                "category": "test",
                "priority": 100,
            },
        ]
        count = retriever.index_entries(entries)
        assert count == 1

    def test_search_score_range(self, retriever: LoreRetriever) -> None:
        entries = [
            {
                "id": "lore_001",
                "name": "Beer",
                "content": "Cold beer served at the tavern.",
                "category": "item",
                "priority": 100,
            },
        ]
        retriever.index_entries(entries)
        results = retriever.search("beer tavern")
        for r in results:
            assert -1.0 <= r.score <= 1.0
