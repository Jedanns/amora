from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class CombatStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"
    DRAW = "draw"

    @property
    def is_finished(self) -> bool:
        return self in {
            CombatStatus.VICTORY,
            CombatStatus.DEFEAT,
            CombatStatus.FLED,
            CombatStatus.DRAW,
        }


class CombatActionType(StrEnum):
    ATTACK = "attack"
    DEFEND = "defend"
    CAST = "cast"
    USE_ITEM = "use_item"
    FLEE = "flee"
    MOVE = "move"
    PASS_TURN = "pass_turn"


class DamageType(StrEnum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"
    HOLY = "holy"
    DARK = "dark"
    TRUE = "true"


class TerrainType(StrEnum):
    OPEN = "open"
    FOREST = "forest"
    CAVE = "cave"
    WATER = "water"
    MOUNTAIN = "mountain"
    URBAN = "urban"
    DUNGEON = "dungeon"


class Position2D(BaseModel):
    x: int = 0
    y: int = 0

    def distance_to(self, other: Position2D) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def is_adjacent(self, other: Position2D, range_: int = 1) -> bool:
        return abs(self.x - other.x) <= range_ and abs(self.y - other.y) <= range_


class TerrainModifiers(BaseModel):
    type: TerrainType = TerrainType.OPEN
    defense_bonus: int = 0
    attack_penalty: int = 0
    movement_cost: float = 1.0
    description: str = ""


class CombatCondition(BaseModel):
    name: str
    remaining_rounds: int | None = None
    attack_modifier: int = 0
    defense_modifier: int = 0
    damage_modifier: int = 0
    speed_modifier: int = 0
    prevents_action: bool = False
    damage_per_round: int = 0
    source_id: str = ""

    def tick(self) -> bool:
        if self.remaining_rounds is not None:
            self.remaining_rounds -= 1
            return self.remaining_rounds <= 0
        return False


class Combatant(BaseModel):
    character_id: str
    team: str = "enemy"
    initiative: int = 0
    actions_per_turn: int = 1
    actions_remaining: int = 1
    conditions: list[CombatCondition] = Field(default_factory=list)
    position: Position2D | None = None
    is_defending: bool = False

    @property
    def can_act(self) -> bool:
        if self.actions_remaining <= 0:
            return False
        return not any(c.prevents_action for c in self.conditions)

    @property
    def total_attack_modifier(self) -> int:
        return sum(c.attack_modifier for c in self.conditions)

    @property
    def total_defense_modifier(self) -> int:
        base = sum(c.defense_modifier for c in self.conditions)
        if self.is_defending:
            base += 2
        return base

    @property
    def total_damage_modifier(self) -> int:
        return sum(c.damage_modifier for c in self.conditions)

    def reset_turn(self) -> None:
        self.actions_remaining = self.actions_per_turn
        self.is_defending = False

    def tick_conditions(self) -> list[str]:
        expired: list[str] = []
        remaining: list[CombatCondition] = []
        for condition in self.conditions:
            if condition.tick():
                expired.append(condition.name)
            else:
                remaining.append(condition)
        self.conditions = remaining
        return expired


class CombatLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    round: int
    turn: int
    actor_id: str
    action_type: CombatActionType
    target_id: str = ""
    roll_result: int | None = None
    roll_target: int | None = None
    hit: bool | None = None
    damage_dealt: int = 0
    damage_type: DamageType = DamageType.PHYSICAL
    narrative: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_narrative_string(self) -> str:
        if self.narrative:
            return self.narrative
        parts = [f"Round {self.round}:"]
        parts.append(f"{self.actor_id} uses {self.action_type.value}")
        if self.target_id:
            parts.append(f"on {self.target_id}")
        if self.roll_result is not None:
            parts.append(f"(roll: {self.roll_result}")
            if self.roll_target is not None:
                parts.append(f"vs AC {self.roll_target}")
            parts.append(")")
        if self.hit is True and self.damage_dealt > 0:
            parts.append(f"dealing {self.damage_dealt} {self.damage_type.value} damage")
        elif self.hit is False:
            parts.append("- miss!")
        return " ".join(parts)


class CombatAction(BaseModel):
    type: CombatActionType
    actor_id: str
    target_id: str = ""
    item_id: str = ""
    spell_name: str = ""
    notation: str = ""


class CombatState(BaseModel):
    id: str = Field(default_factory=lambda: f"combat_{uuid4().hex[:8]}")
    participants: list[Combatant] = Field(default_factory=list)
    turn_order: list[str] = Field(default_factory=list)
    current_turn_index: int = 0
    round: int = 1
    terrain: TerrainModifiers | None = None
    status: CombatStatus = CombatStatus.PENDING
    log: list[CombatLogEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def current_combatant_id(self) -> str | None:
        if not self.turn_order:
            return None
        if self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    @property
    def is_finished(self) -> bool:
        return self.status.is_finished

    def get_combatant(self, character_id: str) -> Combatant | None:
        for p in self.participants:
            if p.character_id == character_id:
                return p
        return None

    def get_teams(self) -> dict[str, list[Combatant]]:
        teams: dict[str, list[Combatant]] = {}
        for p in self.participants:
            teams.setdefault(p.team, []).append(p)
        return teams

    def to_context_string(self) -> str:
        lines = [
            f"[Combat: {self.status.value}] Round {self.round}",
        ]
        if self.terrain:
            lines.append(f"Terrain: {self.terrain.type.value}")
        current = self.current_combatant_id
        for p in self.participants:
            marker = " << ACTIVE" if p.character_id == current else ""
            conds = ", ".join(c.name for c in p.conditions) if p.conditions else "none"
            lines.append(
                f"  {p.character_id} (team:{p.team}, init:{p.initiative}, "
                f"actions:{p.actions_remaining}/{p.actions_per_turn}, "
                f"conditions:{conds}){marker}"
            )
        return "\n".join(lines)
