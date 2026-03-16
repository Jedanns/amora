from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class LorebookCategory(StrEnum):
    CONSTANT = "constant"
    CHARACTER_ACTIVE = "character_active"
    QUEST_STATE = "quest_state"
    LOCATION_ACTIVE = "location_active"
    NPC_PRESENT = "npc_present"
    CONDITIONAL = "conditional"
    AMBIENT = "ambient"
    SECRET = "secret"


class InjectionPosition(StrEnum):
    AFTER_SYSTEM = "after_system"
    AFTER_SCENARIO = "after_scenario"
    BEFORE_EXAMPLE = "before_example"
    AFTER_EXAMPLE = "after_example"


CATEGORY_DEFAULTS: dict[LorebookCategory, dict[str, int]] = {
    LorebookCategory.CONSTANT: {
        "priority": 1000,
        "scan_depth": 0,
        "trigger_chance": 100,
    },
    LorebookCategory.CHARACTER_ACTIVE: {
        "priority": 900,
        "scan_depth": 10,
        "trigger_chance": 100,
    },
    LorebookCategory.QUEST_STATE: {
        "priority": 800,
        "scan_depth": 5,
        "trigger_chance": 100,
    },
    LorebookCategory.LOCATION_ACTIVE: {
        "priority": 700,
        "scan_depth": 15,
        "trigger_chance": 100,
    },
    LorebookCategory.NPC_PRESENT: {
        "priority": 600,
        "scan_depth": 20,
        "trigger_chance": 100,
    },
    LorebookCategory.CONDITIONAL: {
        "priority": 400,
        "scan_depth": 30,
        "trigger_chance": 50,
    },
    LorebookCategory.AMBIENT: {"priority": 200, "scan_depth": 50, "trigger_chance": 30},
    LorebookCategory.SECRET: {"priority": 500, "scan_depth": 10, "trigger_chance": 100},
}


class LoreCondition(BaseModel):
    type: str
    key: str
    operator: str = "eq"
    value: str | int | bool = True


class EntryMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author: str = ""
    source_file: str = ""
    tags: list[str] = Field(default_factory=list)
    version: int = 1


class LorebookEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"lore_{uuid4().hex[:8]}")
    name: str = Field(min_length=1, max_length=200)
    category: LorebookCategory = LorebookCategory.CONDITIONAL

    keys: list[str] = Field(default_factory=list)
    secondary_keys: list[str] = Field(default_factory=list)
    regex_keys: list[str] = Field(default_factory=list)

    content: str = ""
    extensions: dict[str, object] = Field(default_factory=dict)

    priority: int = Field(default=400, ge=0, le=1000)
    order: int = Field(default=100, ge=0)
    position: InjectionPosition = InjectionPosition.AFTER_SYSTEM

    trigger_chance: int = Field(default=100, ge=0, le=100)
    conditions: list[LoreCondition] = Field(default_factory=list)

    use_probability: bool = False
    scan_depth: int = Field(default=30, ge=0)
    case_sensitive: bool = False

    enabled: bool = True
    truncatable: bool = True
    min_tokens: int = Field(default=0, ge=0)

    metadata: EntryMetadata = Field(default_factory=EntryMetadata)

    @property
    def has_keys(self) -> bool:
        return bool(self.keys or self.secondary_keys or self.regex_keys)

    @property
    def is_constant(self) -> bool:
        return self.category == LorebookCategory.CONSTANT

    def apply_category_defaults(self) -> None:
        defaults = CATEGORY_DEFAULTS.get(self.category)
        if defaults:
            self.priority = defaults["priority"]
            self.scan_depth = defaults["scan_depth"]
            self.trigger_chance = defaults["trigger_chance"]

    def effective_priority(self, boost: int = 0) -> int:
        return min(1000, self.priority + boost)

    def to_injection_text(self, variables: dict[str, str] | None = None) -> str:
        text = self.content
        if variables:
            for key, value in variables.items():
                text = text.replace(f"{{{{{key}}}}}", value)
        return text
