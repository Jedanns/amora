from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    status_code: int = 500


class SessionResponse(BaseModel):
    session_id: str
    name: str = ""
    turn: int = 0
    location: str = "spawn"
    combat_active: bool = False
    active_character_id: str | None = None
    version: int = 0


class GameStateResponse(BaseModel):
    session_id: str
    turn: int
    location: str
    combat_active: bool
    active_character_id: str | None
    flags: dict[str, Any] = Field(default_factory=dict)
    version: int


class ActionResponse(BaseModel):
    type: str
    target: str = ""
    value: str = ""
    success: bool = True
    message: str = ""


class DiceRollResponse(BaseModel):
    id: str
    notation: str
    individual: list[int] = Field(default_factory=list)
    modifier: int = 0
    total: int = 0
    reason: str = ""


class NarrativeResponse(BaseModel):
    narrative: str
    actions: list[ActionResponse] = Field(default_factory=list)
    state: GameStateResponse | None = None
    dice_rolls: list[DiceRollResponse] = Field(default_factory=list)


class CharacterResponse(BaseModel):
    id: str
    name: str
    character_class: str
    level: int
    hp_current: int
    hp_max: int
    mana_current: int
    mana_max: int
    location: str
    is_alive: bool
    experience: int
    attributes: dict[str, int] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)


class CharacterListResponse(BaseModel):
    characters: list[CharacterResponse]
    total: int


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    item_type: str
    rarity: str
    quantity: int
    weight: float
    value: int


class InventoryResponse(BaseModel):
    character_id: str
    items: list[ItemResponse] = Field(default_factory=list)
    total_weight: float = 0.0
    max_weight: float = 100.0
    used_slots: int = 0
    max_slots: int = 100


class LoreEntryResponse(BaseModel):
    id: str
    name: str
    content: str
    keys: list[str] = Field(default_factory=list)
    category: str
    priority: int
    enabled: bool


class LoreSearchResultResponse(BaseModel):
    entries: list[LoreEntryResponse]
    query: str
    total: int


class LoreStatsResponse(BaseModel):
    total_entries: int
    categories: dict[str, int] = Field(default_factory=dict)
    enabled_count: int
    disabled_count: int


class LLMHealthResponse(BaseModel):
    healthy: bool
    provider: str = ""
    model: str = ""
    message: str = ""


class GenerationResponse(BaseModel):
    text: str
    tokens_generated: int = 0
    generation_time_ms: float = 0.0
    tokens_per_second: float = 0.0


class HistoryEntryResponse(BaseModel):
    id: str
    timestamp: str
    type: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HistoryResponse(BaseModel):
    entries: list[HistoryEntryResponse]
    total: int


class ObjectiveResponse(BaseModel):
    id: str
    description: str
    current: int
    target: int
    completed: bool


class QuestResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    status: str
    objectives: list[ObjectiveResponse] = Field(default_factory=list)
    progress: float = 0.0


class QuestListResponse(BaseModel):
    quests: list[QuestResponse]
    total: int


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    version: str = ""
    uptime_seconds: float = 0.0
