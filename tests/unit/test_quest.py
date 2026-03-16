import pytest

from src.core.exceptions import QuestError, ValidationError
from src.quest.manager import QuestManager
from src.quest.models import (
    Objective,
    ObjectiveType,
    Quest,
    QuestStatus,
)


class TestObjective:
    def test_creation(self) -> None:
        obj = Objective(
            description="Kill the dragon", type=ObjectiveType.KILL, target="dragon"
        )
        assert not obj.is_complete
        assert obj.progress_pct == 0.0

    def test_advance(self) -> None:
        obj = Objective(description="Collect 5 gems", required=5)
        obj.advance(3)
        assert obj.current == 3
        assert not obj.is_complete
        assert obj.progress_pct == 60.0

    def test_complete(self) -> None:
        obj = Objective(description="Talk to NPC", required=1)
        just_completed = obj.advance(1)
        assert just_completed
        assert obj.is_complete
        assert obj.progress_pct == 100.0

    def test_advance_does_not_exceed(self) -> None:
        obj = Objective(description="Collect 3", required=3)
        obj.advance(10)
        assert obj.current == 3


class TestQuest:
    def test_creation(self, sample_quest: Quest) -> None:
        assert sample_quest.status == QuestStatus.AVAILABLE
        assert len(sample_quest.objectives) == 3

    def test_progress(self, sample_quest: Quest) -> None:
        assert sample_quest.progress_pct == 0.0
        sample_quest.objectives[0].advance(1)
        assert sample_quest.progress_pct > 0.0

    def test_all_required_complete(self, sample_quest: Quest) -> None:
        for obj in sample_quest.objectives:
            obj.advance(obj.required)
        assert sample_quest.all_required_complete
        assert sample_quest.all_complete

    def test_timed_out(self) -> None:
        quest = Quest(name="Timed Quest", time_limit=5, turns_elapsed=5)
        assert quest.is_timed_out

    def test_not_timed_out(self) -> None:
        quest = Quest(name="Timed Quest", time_limit=5, turns_elapsed=3)
        assert not quest.is_timed_out

    def test_no_time_limit(self) -> None:
        quest = Quest(name="Free Quest")
        assert not quest.is_timed_out


class TestQuestManager:
    def test_add_quest(self, quest_manager: QuestManager, sample_quest: Quest) -> None:
        quest_manager.add(sample_quest)
        found = quest_manager.get(sample_quest.id)
        assert found.id == sample_quest.id

    def test_add_duplicate(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        with pytest.raises(QuestError):
            quest_manager.add(sample_quest)

    def test_get_not_found(self, quest_manager: QuestManager) -> None:
        with pytest.raises(QuestError):
            quest_manager.get("nonexistent")

    def test_start_quest(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        started = quest_manager.start(sample_quest.id)
        assert started.status == QuestStatus.ACTIVE
        assert started.metadata.started_at is not None

    def test_start_already_active(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        quest_manager.start(sample_quest.id)
        with pytest.raises(ValidationError):
            quest_manager.start(sample_quest.id)

    def test_advance_objective(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        quest_manager.start(sample_quest.id)
        obj_id = sample_quest.objectives[0].id
        quest_manager.advance_objective(sample_quest.id, obj_id)
        assert sample_quest.objectives[0].is_complete

    def test_auto_complete_on_all_objectives(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        quest_manager.start(sample_quest.id)
        for obj in sample_quest.objectives:
            quest_manager.advance_objective(sample_quest.id, obj.id, obj.required)
        assert sample_quest.status == QuestStatus.COMPLETED

    def test_fail_quest(self, quest_manager: QuestManager, sample_quest: Quest) -> None:
        quest_manager.add(sample_quest)
        quest_manager.start(sample_quest.id)
        quest_manager.fail(sample_quest.id)
        assert sample_quest.status == QuestStatus.FAILED

    def test_abandon_quest(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        quest_manager.start(sample_quest.id)
        quest_manager.abandon(sample_quest.id)
        assert sample_quest.status == QuestStatus.ABANDONED

    def test_tick_turn_timeout(self, quest_manager: QuestManager) -> None:
        quest = Quest(name="Timed", time_limit=2)
        quest_manager.add(quest)
        quest_manager.start(quest.id)
        failed = quest_manager.tick_turn()
        assert len(failed) == 0
        failed = quest_manager.tick_turn()
        assert quest.id in failed
        assert quest.status == QuestStatus.FAILED

    def test_list_active(
        self, quest_manager: QuestManager, sample_quest: Quest
    ) -> None:
        quest_manager.add(sample_quest)
        assert len(quest_manager.list_active()) == 0
        quest_manager.start(sample_quest.id)
        assert len(quest_manager.list_active()) == 1

    def test_export_import(self, quest_manager: QuestManager) -> None:
        quest_manager.add(Quest(name="Quest A"))
        quest_manager.add(Quest(name="Quest B"))
        data = quest_manager.export_all()
        assert len(data) == 2

        new_manager = QuestManager()
        count = new_manager.import_quests(data)
        assert count == 2
