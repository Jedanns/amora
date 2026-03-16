from __future__ import annotations

import aiosqlite
import pytest
import pytest_asyncio

from src.memory.memory_store import MemoryStore
from src.memory.summary import FactType, KeyFact, Summary


@pytest_asyncio.fixture
async def db_connection():
    conn = await aiosqlite.connect(":memory:")
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def memory_store(db_connection: aiosqlite.Connection):
    store = MemoryStore(db_connection)
    await store.initialize()
    return store


class TestMemoryStoreInit:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, db_connection: aiosqlite.Connection):
        store = MemoryStore(db_connection)
        await store.initialize()

        cursor = await db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='summaries'"
        )
        row = await cursor.fetchone()
        assert row is not None

        cursor = await db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='key_facts'"
        )
        row = await cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, db_connection: aiosqlite.Connection):
        store = MemoryStore(db_connection)
        await store.initialize()
        await store.initialize()


class TestSummaryPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load_summary(self, memory_store: MemoryStore):
        summary = Summary(
            text="Le joueur a exploré la forêt.",
            message_range=("msg_1", "msg_30"),
            token_count=50,
        )
        row_id = await memory_store.save_summary("sess_1", summary)
        assert row_id > 0

        loaded = await memory_store.load_latest_summary("sess_1")
        assert loaded is not None
        assert loaded.text == "Le joueur a exploré la forêt."
        assert loaded.message_range == ("msg_1", "msg_30")
        assert loaded.token_count == 50

    @pytest.mark.asyncio
    async def test_load_latest_returns_most_recent(self, memory_store: MemoryStore):
        s1 = Summary(text="First", message_range=("a", "b"), token_count=10)
        s2 = Summary(text="Second", message_range=("c", "d"), token_count=20)
        await memory_store.save_summary("sess_1", s1)
        await memory_store.save_summary("sess_1", s2)

        loaded = await memory_store.load_latest_summary("sess_1")
        assert loaded is not None
        assert loaded.text == "Second"

    @pytest.mark.asyncio
    async def test_load_latest_nonexistent_session(self, memory_store: MemoryStore):
        loaded = await memory_store.load_latest_summary("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_all_summaries(self, memory_store: MemoryStore):
        for i in range(3):
            s = Summary(text=f"Summary {i}", token_count=i * 10)
            await memory_store.save_summary("sess_1", s)

        all_summaries = await memory_store.load_all_summaries("sess_1")
        assert len(all_summaries) == 3
        assert all_summaries[0].text == "Summary 0"
        assert all_summaries[2].text == "Summary 2"

    @pytest.mark.asyncio
    async def test_get_summary_count(self, memory_store: MemoryStore):
        assert await memory_store.get_summary_count("sess_1") == 0
        await memory_store.save_summary("sess_1", Summary(text="A"))
        await memory_store.save_summary("sess_1", Summary(text="B"))
        assert await memory_store.get_summary_count("sess_1") == 2

    @pytest.mark.asyncio
    async def test_summaries_isolated_by_session(self, memory_store: MemoryStore):
        await memory_store.save_summary("sess_1", Summary(text="S1"))
        await memory_store.save_summary("sess_2", Summary(text="S2"))

        s1 = await memory_store.load_latest_summary("sess_1")
        s2 = await memory_store.load_latest_summary("sess_2")
        assert s1 is not None and s1.text == "S1"
        assert s2 is not None and s2.text == "S2"


class TestKeyFactPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load_fact(self, memory_store: MemoryStore):
        fact = KeyFact(
            id="fact_001",
            type=FactType.DEATH,
            content="Le garde est mort",
            confidence=0.9,
            source_message_id="msg_42",
        )
        await memory_store.save_fact("sess_1", fact)

        facts = await memory_store.load_active_facts("sess_1")
        assert len(facts) == 1
        assert facts[0].id == "fact_001"
        assert facts[0].type == FactType.DEATH
        assert facts[0].content == "Le garde est mort"
        assert facts[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_save_facts_batch(self, memory_store: MemoryStore):
        facts = [
            KeyFact(id=f"fact_{i}", type=FactType.STATE_CHANGE, content=f"Fact {i}")
            for i in range(5)
        ]
        count = await memory_store.save_facts("sess_1", facts)
        assert count == 5

        loaded = await memory_store.load_active_facts("sess_1")
        assert len(loaded) == 5

    @pytest.mark.asyncio
    async def test_save_fact_upsert(self, memory_store: MemoryStore):
        fact1 = KeyFact(id="fact_dup", type=FactType.DEATH, content="Version 1")
        await memory_store.save_fact("sess_1", fact1)

        fact2 = KeyFact(id="fact_dup", type=FactType.DEATH, content="Version 2")
        await memory_store.save_fact("sess_1", fact2)

        facts = await memory_store.load_active_facts("sess_1")
        assert len(facts) == 1
        assert facts[0].content == "Version 2"

    @pytest.mark.asyncio
    async def test_load_facts_by_type(self, memory_store: MemoryStore):
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f1", type=FactType.DEATH, content="Death fact"),
        )
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f2", type=FactType.ITEM_ACQUIRED, content="Item fact"),
        )
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f3", type=FactType.DEATH, content="Another death"),
        )

        death_facts = await memory_store.load_active_facts(
            "sess_1", fact_type="death"
        )
        assert len(death_facts) == 2

        item_facts = await memory_store.load_active_facts(
            "sess_1", fact_type="item_acquired"
        )
        assert len(item_facts) == 1

    @pytest.mark.asyncio
    async def test_deactivate_fact(self, memory_store: MemoryStore):
        fact = KeyFact(id="fact_del", type=FactType.STATE_CHANGE, content="Temp")
        await memory_store.save_fact("sess_1", fact)

        result = await memory_store.deactivate_fact("fact_del")
        assert result is True

        active = await memory_store.load_active_facts("sess_1")
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent(self, memory_store: MemoryStore):
        result = await memory_store.deactivate_fact("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_fact_count(self, memory_store: MemoryStore):
        assert await memory_store.get_fact_count("sess_1") == 0
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f1", type=FactType.DEATH, content="A"),
        )
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f2", type=FactType.DEATH, content="B"),
        )
        assert await memory_store.get_fact_count("sess_1") == 2

    @pytest.mark.asyncio
    async def test_load_facts_respects_limit(self, memory_store: MemoryStore):
        for i in range(10):
            await memory_store.save_fact(
                "sess_1",
                KeyFact(id=f"fact_{i}", type=FactType.STATE_CHANGE, content=f"F{i}"),
            )
        facts = await memory_store.load_active_facts("sess_1", limit=3)
        assert len(facts) == 3

    @pytest.mark.asyncio
    async def test_facts_isolated_by_session(self, memory_store: MemoryStore):
        await memory_store.save_fact(
            "sess_1", KeyFact(id="f1", type=FactType.DEATH, content="S1 fact")
        )
        await memory_store.save_fact(
            "sess_2", KeyFact(id="f2", type=FactType.DEATH, content="S2 fact")
        )

        s1_facts = await memory_store.load_active_facts("sess_1")
        s2_facts = await memory_store.load_active_facts("sess_2")
        assert len(s1_facts) == 1
        assert len(s2_facts) == 1
        assert s1_facts[0].content == "S1 fact"


class TestClearSessionMemory:
    @pytest.mark.asyncio
    async def test_clear_removes_all(self, memory_store: MemoryStore):
        await memory_store.save_summary("sess_1", Summary(text="S"))
        await memory_store.save_fact(
            "sess_1",
            KeyFact(id="f1", type=FactType.DEATH, content="F"),
        )

        await memory_store.clear_session_memory("sess_1")

        assert await memory_store.get_summary_count("sess_1") == 0
        assert await memory_store.get_fact_count("sess_1") == 0

    @pytest.mark.asyncio
    async def test_clear_only_affects_target_session(self, memory_store: MemoryStore):
        await memory_store.save_summary("sess_1", Summary(text="S1"))
        await memory_store.save_summary("sess_2", Summary(text="S2"))

        await memory_store.clear_session_memory("sess_1")

        assert await memory_store.get_summary_count("sess_1") == 0
        assert await memory_store.get_summary_count("sess_2") == 1
