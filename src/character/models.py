from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class CharacterClass(StrEnum):
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"
    BARD = "bard"
    PALADIN = "paladin"
    CUSTOM = "custom"


class Rarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"


class ConditionType(StrEnum):
    BUFF = "buff"
    DEBUFF = "debuff"
    POISON = "poison"
    DISEASE = "disease"
    CURSE = "curse"
    BLESSING = "blessing"


class DurationType(StrEnum):
    PERMANENT = "permanent"
    ROUNDS = "rounds"
    TIME = "time"


class StatPool(BaseModel):
    current: int = Field(ge=0)
    max: int = Field(ge=1)
    temporary_bonus: int = 0
    temporary_max_increase: int = 0

    @model_validator(mode="after")
    def validate_current_le_max(self) -> StatPool:
        effective_max = self.max + self.temporary_max_increase
        if self.current > effective_max:
            self.current = effective_max
        return self

    def apply_damage(self, amount: int) -> int:
        actual = min(amount, self.current)
        self.current = max(0, self.current - amount)
        return actual

    def apply_heal(self, amount: int) -> int:
        effective_max = self.max + self.temporary_max_increase
        before = self.current
        self.current = min(effective_max, self.current + amount)
        return self.current - before

    @property
    def effective_max(self) -> int:
        return self.max + self.temporary_max_increase

    @property
    def is_depleted(self) -> bool:
        return self.current <= 0

    @property
    def percentage(self) -> float:
        if self.effective_max == 0:
            return 0.0
        return (self.current / self.effective_max) * 100.0


class Attributes(BaseModel):
    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)

    def get_modifier(self, attribute: str) -> int:
        value = getattr(self, attribute)
        return (value - 10) // 2

    def to_summary(self) -> str:
        parts = []
        for attr in [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]:
            val = getattr(self, attr)
            mod = self.get_modifier(attr)
            sign = "+" if mod >= 0 else ""
            parts.append(f"{attr[:3].upper()}: {val} ({sign}{mod})")
        return " | ".join(parts)


class Condition(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    type: ConditionType
    duration_type: DurationType = DurationType.PERMANENT
    remaining: int | None = None
    effects: dict[str, Any] = Field(default_factory=dict)
    stacks: bool = False
    current_stacks: int = 1
    max_stacks: int = 1
    source: str | None = None
    dispellable: bool = True

    def tick(self) -> bool:
        if self.duration_type == DurationType.ROUNDS and self.remaining is not None:
            self.remaining -= 1
            return self.remaining <= 0
        return False


class Relationship(BaseModel):
    character_id: str
    type: str = "neutral"
    value: int = Field(default=0, ge=-100, le=100)
    notes: str = ""


class CharacterMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_deleted: bool = False
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class Character(BaseModel):
    id: str = Field(default_factory=lambda: f"char_{uuid4().hex[:8]}")
    name: str = Field(min_length=1, max_length=100)
    player_id: str | None = None

    character_class: CharacterClass = CharacterClass.WARRIOR
    level: int = Field(default=1, ge=1, le=20)
    experience: int = Field(default=0, ge=0)

    hp: StatPool = Field(default_factory=lambda: StatPool(current=20, max=20))
    mana: StatPool = Field(default_factory=lambda: StatPool(current=10, max=10))
    stamina: StatPool = Field(default_factory=lambda: StatPool(current=10, max=10))
    attributes: Attributes = Field(default_factory=Attributes)

    conditions: list[Condition] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    location: str = "spawn"
    metadata: CharacterMetadata = Field(default_factory=CharacterMetadata)

    @property
    def is_alive(self) -> bool:
        return not self.hp.is_depleted

    @property
    def is_npc(self) -> bool:
        return self.player_id is None

    def experience_for_next_level(self) -> int:
        return self.level * 100

    def can_level_up(self) -> bool:
        return self.experience >= self.experience_for_next_level()

    def level_up(self, hp_per_level: int = 10, mana_per_level: int = 5) -> bool:
        if not self.can_level_up():
            return False
        self.experience -= self.experience_for_next_level()
        self.level += 1
        self.hp.max += hp_per_level
        self.hp.current = self.hp.max
        self.mana.max += mana_per_level
        self.mana.current = self.mana.max
        self.metadata.updated_at = datetime.now(UTC)
        return True

    def add_condition(self, condition: Condition) -> None:
        existing = next((c for c in self.conditions if c.name == condition.name), None)
        if existing and existing.stacks:
            existing.current_stacks = min(
                existing.current_stacks + 1, existing.max_stacks
            )
        elif existing and not existing.stacks:
            existing.remaining = condition.remaining
        else:
            self.conditions.append(condition)
        self.metadata.updated_at = datetime.now(UTC)

    def remove_condition(self, condition_name: str) -> bool:
        before = len(self.conditions)
        self.conditions = [c for c in self.conditions if c.name != condition_name]
        if len(self.conditions) < before:
            self.metadata.updated_at = datetime.now(UTC)
            return True
        return False

    def tick_conditions(self) -> list[str]:
        expired: list[str] = []
        remaining: list[Condition] = []
        for condition in self.conditions:
            if condition.tick():
                expired.append(condition.name)
            else:
                remaining.append(condition)
        self.conditions = remaining
        if expired:
            self.metadata.updated_at = datetime.now(UTC)
        return expired

    def to_context_string(self) -> str:
        lines = [
            f"[{self.name}] Niveau {self.level} {self.character_class.value}",
            f"PV: {self.hp.current}/{self.hp.effective_max} | "
            f"Mana: {self.mana.current}/{self.mana.effective_max} | "
            f"Stamina: {self.stamina.current}/{self.stamina.effective_max}",
            self.attributes.to_summary(),
        ]
        if self.conditions:
            conditions_str = ", ".join(c.name for c in self.conditions)
            lines.append(f"Conditions: {conditions_str}")
        lines.append(f"Position: {self.location}")
        return "\n".join(lines)
