from __future__ import annotations

from datetime import UTC, datetime

from src.core.exceptions import QuestError, ValidationError
from src.quest.models import Quest, QuestStatus


class QuestManager:
    def __init__(self) -> None:
        self._quests: dict[str, Quest] = {}

    def add(self, quest: Quest) -> Quest:
        if quest.id in self._quests:
            raise QuestError(
                f"Quest already exists: {quest.id}",
                context={"quest_id": quest.id},
            )
        self._quests[quest.id] = quest
        return quest

    def get(self, quest_id: str) -> Quest:
        quest = self._quests.get(quest_id)
        if quest is None:
            raise QuestError(
                f"Quest not found: {quest_id}",
                context={"quest_id": quest_id},
            )
        return quest

    def start(self, quest_id: str) -> Quest:
        quest = self.get(quest_id)
        if quest.status != QuestStatus.AVAILABLE:
            raise ValidationError(
                f"Quest {quest_id} is not available (status: {quest.status.value})"
            )
        for prereq_id in quest.prerequisites:
            prereq = self._quests.get(prereq_id)
            if prereq is None or prereq.status != QuestStatus.COMPLETED:
                raise ValidationError(f"Prerequisite quest not completed: {prereq_id}")
        quest.status = QuestStatus.ACTIVE
        quest.metadata.started_at = datetime.now(UTC)
        return quest

    def advance_objective(
        self, quest_id: str, objective_id: str, amount: int = 1
    ) -> bool:
        quest = self.get(quest_id)
        if quest.status != QuestStatus.ACTIVE:
            raise ValidationError(
                f"Quest {quest_id} is not active (status: {quest.status.value})"
            )
        objective = next((o for o in quest.objectives if o.id == objective_id), None)
        if objective is None:
            raise QuestError(
                f"Objective not found: {objective_id}",
                context={"quest_id": quest_id, "objective_id": objective_id},
            )
        just_completed = objective.advance(amount)
        if quest.all_required_complete:
            self.complete(quest_id)
        return just_completed

    def complete(self, quest_id: str) -> Quest:
        quest = self.get(quest_id)
        if quest.status != QuestStatus.ACTIVE:
            raise ValidationError(
                f"Quest {quest_id} is not active (status: {quest.status.value})"
            )
        quest.status = QuestStatus.COMPLETED
        quest.metadata.completed_at = datetime.now(UTC)
        return quest

    def fail(self, quest_id: str) -> Quest:
        quest = self.get(quest_id)
        if quest.status != QuestStatus.ACTIVE:
            raise ValidationError(
                f"Quest {quest_id} is not active (status: {quest.status.value})"
            )
        quest.status = QuestStatus.FAILED
        return quest

    def abandon(self, quest_id: str) -> Quest:
        quest = self.get(quest_id)
        if quest.status != QuestStatus.ACTIVE:
            raise ValidationError(
                f"Quest {quest_id} is not active (status: {quest.status.value})"
            )
        quest.status = QuestStatus.ABANDONED
        return quest

    def tick_turn(self) -> list[str]:
        failed: list[str] = []
        for quest in self._quests.values():
            if quest.status == QuestStatus.ACTIVE and quest.time_limit is not None:
                quest.turns_elapsed += 1
                if quest.is_timed_out:
                    quest.status = QuestStatus.FAILED
                    failed.append(quest.id)
        return failed

    def list_active(self) -> list[Quest]:
        return [q for q in self._quests.values() if q.status == QuestStatus.ACTIVE]

    def list_available(self) -> list[Quest]:
        return [q for q in self._quests.values() if q.status == QuestStatus.AVAILABLE]

    def list_completed(self) -> list[Quest]:
        return [q for q in self._quests.values() if q.status == QuestStatus.COMPLETED]

    def export_all(self) -> list[dict[str, object]]:
        return [q.model_dump(mode="json") for q in self._quests.values()]

    def import_quests(self, data: list[dict[str, object]]) -> int:
        count = 0
        for quest_data in data:
            quest = Quest.model_validate(quest_data)
            self._quests[quest.id] = quest
            count += 1
        return count
