from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.memory.summary import KeyFact, Summary

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)

MEMORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    message_range_start TEXT NOT NULL DEFAULT '',
    message_range_end TEXT NOT NULL DEFAULT '',
    previous_summary_id TEXT NOT NULL DEFAULT '',
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS key_facts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_message_id TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    extracted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_key_facts_session ON key_facts(session_id);
CREATE INDEX IF NOT EXISTS idx_key_facts_type ON key_facts(session_id, type);
CREATE INDEX IF NOT EXISTS idx_key_facts_active ON key_facts(session_id, active);
"""


class MemoryStore:
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._conn = connection

    async def initialize(self) -> None:
        await self._conn.executescript(MEMORY_SCHEMA_SQL)
        await self._conn.commit()
        logger.info("MemoryStore tables initialized")

    async def save_summary(self, session_id: str, summary: Summary) -> int:
        cursor = await self._conn.execute(
            """
            INSERT INTO summaries
                (session_id, summary_text, message_range_start, message_range_end,
                 previous_summary_id, token_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                summary.text,
                summary.message_range[0],
                summary.message_range[1],
                summary.previous_summary_id,
                summary.token_count,
            ),
        )
        await self._conn.commit()
        return cursor.lastrowid or 0

    async def load_latest_summary(self, session_id: str) -> Summary | None:
        cursor = await self._conn.execute(
            """
            SELECT summary_text, message_range_start, message_range_end,
                   previous_summary_id, token_count, created_at
            FROM summaries
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        return Summary(
            text=row[0],
            message_range=(row[1], row[2]),
            previous_summary_id=row[3],
            token_count=row[4],
        )

    async def load_all_summaries(self, session_id: str) -> list[Summary]:
        cursor = await self._conn.execute(
            """
            SELECT summary_text, message_range_start, message_range_end,
                   previous_summary_id, token_count, created_at
            FROM summaries
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [
            Summary(
                text=row[0],
                message_range=(row[1], row[2]),
                previous_summary_id=row[3],
                token_count=row[4],
            )
            for row in rows
        ]

    async def save_fact(self, session_id: str, fact: KeyFact) -> None:
        await self._conn.execute(
            """
            INSERT INTO key_facts
                (id, session_id, type, content, confidence,
                 source_message_id, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content = excluded.content,
                confidence = excluded.confidence
            """,
            (
                fact.id,
                session_id,
                fact.type.value,
                fact.content,
                fact.confidence,
                fact.source_message_id,
                fact.extracted_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def save_facts(self, session_id: str, facts: list[KeyFact]) -> int:
        count = 0
        for fact in facts:
            await self.save_fact(session_id, fact)
            count += 1
        return count

    async def load_active_facts(
        self,
        session_id: str,
        fact_type: str | None = None,
        limit: int = 50,
    ) -> list[KeyFact]:
        if fact_type:
            cursor = await self._conn.execute(
                """
                SELECT id, type, content, confidence, source_message_id, extracted_at
                FROM key_facts
                WHERE session_id = ? AND active = 1 AND type = ?
                ORDER BY extracted_at DESC
                LIMIT ?
                """,
                (session_id, fact_type, limit),
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT id, type, content, confidence, source_message_id, extracted_at
                FROM key_facts
                WHERE session_id = ? AND active = 1
                ORDER BY extracted_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def deactivate_fact(self, fact_id: str) -> bool:
        cursor = await self._conn.execute(
            "UPDATE key_facts SET active = 0 WHERE id = ?",
            (fact_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get_fact_count(self, session_id: str) -> int:
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM key_facts WHERE session_id = ? AND active = 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_summary_count(self, session_id: str) -> int:
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def clear_session_memory(self, session_id: str) -> None:
        await self._conn.execute(
            "DELETE FROM summaries WHERE session_id = ?", (session_id,)
        )
        await self._conn.execute(
            "DELETE FROM key_facts WHERE session_id = ?", (session_id,)
        )
        await self._conn.commit()
        logger.info("Cleared memory for session: %s", session_id)

    @staticmethod
    def _row_to_fact(row: Any) -> KeyFact:
        from src.memory.summary import FactType

        return KeyFact(
            id=row[0],
            type=FactType(row[1]),
            content=row[2],
            confidence=row[3],
            source_message_id=row[4],
        )
