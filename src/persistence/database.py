from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from src.memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS dice_rolls (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    notation TEXT NOT NULL,
    total INTEGER NOT NULL,
    data JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS game_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    state_data JSON NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_characters_session ON characters(session_id);
CREATE INDEX IF NOT EXISTS idx_dice_rolls_session ON dice_rolls(session_id);
CREATE INDEX IF NOT EXISTS idx_game_states_session ON game_states(session_id);
CREATE INDEX IF NOT EXISTS idx_game_states_version ON game_states(session_id, version DESC);
"""


class Database:
    def __init__(self, db_path: str = "data/game.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._connection = await aiosqlite.connect(str(self._db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.executescript(SCHEMA_SQL)
        await self._connection.commit()
        logger.info("Database connected: %s", self._db_path)

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database disconnected")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    async def save_session(
        self, session_id: str, name: str, data: dict[str, Any]
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO sessions (id, name, data, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                data = excluded.data,
                updated_at = datetime('now')
            """,
            (session_id, name, json.dumps(data)),
        )
        await self.conn.commit()

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT data FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])  # type: ignore[no-any-return]

    async def list_sessions(self) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT id, name, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]

    async def delete_session(self, session_id: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def save_character(
        self, session_id: str, character_id: str, name: str, data: dict[str, Any]
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO characters (id, session_id, name, data, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                data = excluded.data,
                updated_at = datetime('now')
            """,
            (character_id, session_id, name, json.dumps(data)),
        )
        await self.conn.commit()

    async def load_characters(self, session_id: str) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT data FROM characters WHERE session_id = ?", (session_id,)
        )
        rows = await cursor.fetchall()
        return [json.loads(r[0]) for r in rows]

    async def save_dice_roll(
        self,
        session_id: str,
        roll_id: str,
        notation: str,
        total: int,
        data: dict[str, Any],
    ) -> None:
        await self.conn.execute(
            "INSERT INTO dice_rolls (id, session_id, notation, total, data) VALUES (?, ?, ?, ?, ?)",
            (roll_id, session_id, notation, total, json.dumps(data)),
        )
        await self.conn.commit()

    async def save_game_state(
        self, session_id: str, state_data: dict[str, Any], version: int
    ) -> None:
        await self.conn.execute(
            "INSERT INTO game_states (session_id, state_data, version) VALUES (?, ?, ?)",
            (session_id, json.dumps(state_data), version),
        )
        await self.conn.commit()

    async def load_latest_state(self, session_id: str) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT state_data FROM game_states WHERE session_id = ? ORDER BY version DESC LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])  # type: ignore[no-any-return]

    async def create_memory_store(self) -> MemoryStore:
        from src.memory.memory_store import MemoryStore

        store = MemoryStore(self.conn)
        await store.initialize()
        return store
