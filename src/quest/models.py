from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class QuestType(StrEnum):
    MAIN = "main"
    SIDE = "side"
    BOUNTY = "bounty"
    ESCORT = "escort"
    FETCH = "fetch"
    KILL = "kill"
    EXPLORE = "explore"


class QuestStatus(StrEnum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ObjectiveType(StrEnum):
    KILL = "kill"
    COLLECT = "collect"
    DELIVER = "deliver"
    TALK = "talk"
    EXPLORE = "explore"
    ESCORT = "escort"
    SURVIVE = "survive"
    CUSTOM = "custom"


class Objective(BaseModel):
    id: str = Field(default_factory=lambda: f"obj_{uuid4().hex[:8]}")
    description: str
    type: ObjectiveType = ObjectiveType.CUSTOM
    target: str = ""
    current: int = Field(default=0, ge=0)
    required: int = Field(default=1, ge=1)
    optional: bool = False
    hidden: bool = False

    @property
    def is_complete(self) -> bool:
        return self.current >= self.required

    @property
    def progress_pct(self) -> float:
        if self.required == 0:
            return 100.0
        return min(100.0, (self.current / self.required) * 100.0)

    def advance(self, amount: int = 1) -> bool:
        before = self.is_complete
        self.current = min(self.current + amount, self.required)
        return not before and self.is_complete


class Reward(BaseModel):
    experience: int = 0
    gold: int = 0
    items: list[str] = Field(default_factory=list)
    reputation: dict[str, int] = Field(default_factory=dict)


class QuestMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    giver_id: str = ""
    chapter: str = ""


class Quest(BaseModel):
    id: str = Field(default_factory=lambda: f"quest_{uuid4().hex[:8]}")
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

    type: QuestType = QuestType.SIDE
    status: QuestStatus = QuestStatus.AVAILABLE

    objectives: list[Objective] = Field(default_factory=list)
    rewards: Reward = Field(default_factory=Reward)

    prerequisites: list[str] = Field(default_factory=list)
    unlocks: list[str] = Field(default_factory=list)

    time_limit: int | None = None
    turns_elapsed: int = 0
    repeatable: bool = False

    metadata: QuestMetadata = Field(default_factory=QuestMetadata)

    @property
    def is_timed_out(self) -> bool:
        if self.time_limit is None:
            return False
        return self.turns_elapsed >= self.time_limit

    @property
    def all_required_complete(self) -> bool:
        required = [o for o in self.objectives if not o.optional]
        return all(o.is_complete for o in required)

    @property
    def all_complete(self) -> bool:
        return all(o.is_complete for o in self.objectives)

    @property
    def progress_pct(self) -> float:
        if not self.objectives:
            return 0.0
        required = [o for o in self.objectives if not o.optional]
        if not required:
            return 100.0
        return sum(o.progress_pct for o in required) / len(required)
