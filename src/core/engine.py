from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.character.manager import CharacterManager
from src.character.models import Character, CharacterClass
from src.core.config import Config, load_config
from src.core.dice import DiceResult, DiceRoller, RollContext
from src.core.events import EventBus, EventType, GameEvent
from src.core.exceptions import SessionError, StateError
from src.inventory.manager import Inventory, InventoryConfig
from src.persistence.database import Database
from src.persistence.files import FileStorage
from src.quest.manager import QuestManager

if TYPE_CHECKING:
    from src.inventory.item import Item

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    session_id: str
    name: str = "New Session"
    turn: int = 0
    active_character_id: str | None = None
    location: str = "spawn"
    combat_active: bool = False
    flags: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def copy(self) -> GameState:
        return GameState(
            session_id=self.session_id,
            name=self.name,
            turn=self.turn,
            active_character_id=self.active_character_id,
            location=self.location,
            combat_active=self.combat_active,
            flags=dict(self.flags),
            version=self.version,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "turn": self.turn,
            "active_character_id": self.active_character_id,
            "location": self.location,
            "combat_active": self.combat_active,
            "flags": self.flags,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(UTC)
        return cls(
            session_id=data["session_id"],
            name=data.get("name", data["session_id"]),
            turn=data.get("turn", 0),
            active_character_id=data.get("active_character_id"),
            location=data.get("location", "spawn"),
            combat_active=data.get("combat_active", False),
            flags=data.get("flags", {}),
            version=data.get("version", 0),
            timestamp=ts,
        )


@dataclass
class HistoryEntry:
    id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    type: str = "system"
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }


class GameEngine:
    MAX_HISTORY: int = 100

    def __init__(
        self,
        config: Config | None = None,
        database: Database | None = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        self._config = config or load_config()
        self._db = database or Database(self._config.persistence.database)
        self._files = file_storage or FileStorage()

        self._events = EventBus()
        self._dice = DiceRoller(seed=self._config.game.dice.seed)
        self._characters = CharacterManager()
        self._quests = QuestManager()

        self._state: GameState | None = None
        self._state_history: deque[GameState] = deque(maxlen=self.MAX_HISTORY)
        self._history: list[HistoryEntry] = []
        self._inventories: dict[str, Inventory] = {}

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def state(self) -> GameState:
        if self._state is None:
            raise SessionError("No active session. Call create_session() first.")
        return self._state

    @property
    def characters(self) -> CharacterManager:
        return self._characters

    @property
    def quests(self) -> QuestManager:
        return self._quests

    @property
    def dice(self) -> DiceRoller:
        return self._dice

    @property
    def history(self) -> list[HistoryEntry]:
        return list(self._history)

    async def initialize(self) -> None:
        await self._db.connect()
        logger.info("GameEngine initialized")

    async def shutdown(self) -> None:
        if self._state:
            await self.save_session()
        await self._db.disconnect()
        logger.info("GameEngine shut down")

    async def create_session(
        self, name: str = "New Session", world_id: str = "default"
    ) -> GameState:
        session_id = f"sess_{uuid4().hex[:8]}"
        self._state = GameState(session_id=session_id, name=name, location="spawn")
        self._state_history.clear()
        self._history.clear()

        self._add_history("system", f"Session '{name}' created in world '{world_id}'")

        await self._events.emit(
            GameEvent(
                type=EventType.SESSION_CREATED,
                data={"session_id": session_id, "name": name, "world_id": world_id},
                source="engine",
            )
        )

        logger.info("Session created: %s", session_id)
        return self._state

    async def save_session(self) -> None:
        state = self.state
        session_data = {
            "state": state.to_dict(),
            "characters": self._characters.export_all(),
            "quests": self._quests.export_all(),
            "inventories": {
                cid: inv.model_dump(mode="json")
                for cid, inv in self._inventories.items()
            },
            "history": [h.to_dict() for h in self._history[-100:]],
        }

        await self._db.save_session(state.session_id, state.name, session_data)
        state.version += 1
        await self._db.save_game_state(state.session_id, state.to_dict(), state.version)

        await self._events.emit(
            GameEvent(
                type=EventType.SESSION_SAVED,
                data={"session_id": state.session_id, "version": state.version},
                source="engine",
            )
        )
        logger.info("Session saved: %s (v%d)", state.session_id, state.version)

    async def load_session(self, session_id: str) -> GameState:
        data = await self._db.load_session(session_id)
        if data is None:
            raise SessionError(f"Session not found: {session_id}")

        self._state = GameState.from_dict(data["state"])
        self._characters.import_characters(data.get("characters", []))
        self._quests.import_quests(data.get("quests", []))

        for cid, inv_data in data.get("inventories", {}).items():
            self._inventories[cid] = Inventory.model_validate(inv_data)

        self._history = [HistoryEntry(**h) for h in data.get("history", [])]

        await self._events.emit(
            GameEvent(
                type=EventType.SESSION_LOADED,
                data={"session_id": session_id},
                source="engine",
            )
        )
        logger.info("Session loaded: %s", session_id)
        return self._state

    def create_character(
        self,
        name: str,
        character_class: CharacterClass = CharacterClass.WARRIOR,
        player_id: str | None = None,
    ) -> Character:
        character = self._characters.create(name, character_class, player_id)
        inv_config = InventoryConfig(
            max_slots=self._config.game.inventory.max_slots,
            max_weight=self._config.game.inventory.max_weight,
        )
        self._inventories[character.id] = Inventory(config=inv_config)
        self._add_history(
            "system",
            f"Character created: {name} ({character_class.value})",
            {"character_id": character.id},
        )
        return character

    def get_inventory(self, character_id: str) -> Inventory:
        self._characters.get(character_id)
        if character_id not in self._inventories:
            inv_config = InventoryConfig(
                max_slots=self._config.game.inventory.max_slots,
                max_weight=self._config.game.inventory.max_weight,
            )
            self._inventories[character_id] = Inventory(config=inv_config)
        return self._inventories[character_id]

    def add_item_to_inventory(self, character_id: str, item: Item) -> Item:
        inventory = self.get_inventory(character_id)
        added = inventory.add(item)
        self._add_history(
            "action",
            f"Item added: {item.name} (x{item.quantity})",
            {"character_id": character_id, "item_id": item.id},
        )
        return added

    def roll_dice(
        self,
        notation: str,
        reason: str = "",
        actor_id: str = "",
    ) -> DiceResult:
        context = RollContext(
            reason=reason,
            actor_id=actor_id,
            session_id=self.state.session_id,
        )
        result = self._dice.roll(notation, context)
        self._add_history(
            "roll",
            f"Dice roll: {notation} = {result.total} ({reason})"
            if reason
            else f"Dice roll: {notation} = {result.total}",
            {"roll_id": result.id, "notation": notation, "total": result.total},
        )
        return result

    def advance_turn(self) -> int:
        state = self.state
        self._checkpoint()
        state.turn += 1
        state.timestamp = datetime.now(UTC)

        expired = []
        for character in self._characters.list_active():
            expired_conditions = character.tick_conditions()
            if expired_conditions:
                expired.extend((character.name, c) for c in expired_conditions)

        failed_quests = self._quests.tick_turn()

        self._add_history(
            "system",
            f"Turn {state.turn}",
            {
                "expired_conditions": expired,
                "failed_quests": failed_quests,
            },
        )
        return state.turn

    def rollback(self, steps: int = 1) -> GameState:
        if steps > len(self._state_history):
            raise StateError(
                f"Cannot rollback {steps} steps, "
                f"only {len(self._state_history)} available"
            )
        for _ in range(steps):
            self._state = self._state_history.pop()
        self._add_history("system", f"Rolled back {steps} step(s)")
        return self.state

    def set_flag(self, key: str, value: Any) -> None:
        self.state.flags[key] = value

    def get_flag(self, key: str, default: Any = None) -> Any:
        return self.state.flags.get(key, default)

    def _checkpoint(self) -> None:
        if self._state:
            self._state_history.append(self._state.copy())

    def _add_history(
        self,
        entry_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = HistoryEntry(
            type=entry_type,
            content=content,
            metadata=metadata or {},
        )
        self._history.append(entry)
