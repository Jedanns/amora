from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    name: str = Field(default="New Session", max_length=200)
    world_id: str = Field(default="default", max_length=100)


class ProcessInputRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)


class CreateCharacterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    character_class: str = Field(default="warrior")
    player_id: str | None = None


class AddItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    item_type: str = "misc"
    rarity: str = "common"
    quantity: int = Field(default=1, ge=1)
    weight: float = Field(default=0.0, ge=0.0)
    value: int = Field(default=0, ge=0)


class RollDiceRequest(BaseModel):
    notation: str = Field(..., min_length=1, max_length=50, pattern=r"^\d*[dD]\d+")
    reason: str = ""
    actor_id: str = ""


class AddLoreEntryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    keys: list[str] = Field(default_factory=list)
    secondary_keys: list[str] = Field(default_factory=list)
    category: str = "conditional"
    priority: int = Field(default=400, ge=0, le=1000)
    enabled: bool = True


class SearchLoreRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    n_results: int = Field(default=5, ge=1, le=50)
    category: str | None = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=50000)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stop_sequences: list[str] = Field(default_factory=list)


class QuestUpdateRequest(BaseModel):
    objective_id: str = Field(..., min_length=1)
    amount: int = Field(default=1, ge=1)


class DamageHealRequest(BaseModel):
    amount: int = Field(..., ge=0)


class MoveCharacterRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=200)


class AddExperienceRequest(BaseModel):
    amount: int = Field(..., ge=0)
