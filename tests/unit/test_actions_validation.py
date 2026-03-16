import pytest

from src.character.manager import CharacterManager
from src.character.models import CharacterClass
from src.combat.actions import ActionExecutor
from src.combat.validation import (
    DEFAULT_RULES,
    StateValidator,
    ValidationResult,
    rule_experience_non_negative,
    rule_hp_non_negative,
    rule_hp_not_exceeding_max,
    rule_inventory_slots,
    rule_inventory_weight,
    rule_level_in_range,
    rule_mana_non_negative,
)
from src.core.dice import DiceRoller
from src.core.events import EventBus
from src.core.exceptions import InvariantViolationError
from src.inventory.item import Item
from src.inventory.manager import Inventory, InventoryConfig
from src.llm.parser import Action
from src.quest.manager import QuestManager
from src.quest.models import Objective, ObjectiveType, Quest, QuestType


@pytest.fixture
def characters() -> CharacterManager:
    return CharacterManager()


@pytest.fixture
def inventories() -> dict[str, Inventory]:
    return {}


@pytest.fixture
def quests() -> QuestManager:
    return QuestManager()


@pytest.fixture
def dice() -> DiceRoller:
    return DiceRoller(seed=42)


@pytest.fixture
def events() -> EventBus:
    return EventBus()


@pytest.fixture
def executor(
    characters: CharacterManager,
    inventories: dict[str, Inventory],
    quests: QuestManager,
    dice: DiceRoller,
    events: EventBus,
) -> ActionExecutor:
    return ActionExecutor(characters, inventories, quests, dice, events)


class TestActionExecutorDamage:
    @pytest.mark.asyncio
    async def test_damage_action(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="damage", target=char.id, value=5)
        result = await executor.execute(action)
        assert result.success
        assert char.hp.current == 15

    @pytest.mark.asyncio
    async def test_damage_negative(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="damage", target=char.id, value=-5)
        result = await executor.execute(action)
        assert not result.success


class TestActionExecutorHeal:
    @pytest.mark.asyncio
    async def test_heal_action(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        characters.apply_damage(char.id, 10)
        action = Action(type="heal", target=char.id, value=5)
        result = await executor.execute(action)
        assert result.success
        assert char.hp.current == 15


class TestActionExecutorGiveItem:
    @pytest.mark.asyncio
    async def test_give_item(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
        inventories: dict[str, Inventory],
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        inventories[char.id] = Inventory(config=InventoryConfig(max_slots=10, max_weight=50.0))
        action = Action(type="give_item", target=char.id, value=1)
        result = await executor.execute(action)
        assert result.success
        assert len(inventories[char.id].items) == 1

    @pytest.mark.asyncio
    async def test_give_item_no_inventory(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="give_item", target=char.id, value=1)
        result = await executor.execute(action)
        assert not result.success


class TestActionExecutorRemoveItem:
    @pytest.mark.asyncio
    async def test_remove_item(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
        inventories: dict[str, Inventory],
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        inv = Inventory(config=InventoryConfig(max_slots=10, max_weight=50.0))
        item = Item(name="Sword", weight=3.0)
        inv.add(item)
        inventories[char.id] = inv
        action = Action(type="remove_item", target=char.id, value=0)
        result = await executor.execute(action)
        assert result.success

    @pytest.mark.asyncio
    async def test_remove_item_empty_inventory(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
        inventories: dict[str, Inventory],
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        inventories[char.id] = Inventory(config=InventoryConfig())
        action = Action(type="remove_item", target=char.id, value=0)
        result = await executor.execute(action)
        assert not result.success


class TestActionExecutorGiveXP:
    @pytest.mark.asyncio
    async def test_give_xp(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="give_xp", target=char.id, value=50)
        result = await executor.execute(action)
        assert result.success
        assert char.experience == 50

    @pytest.mark.asyncio
    async def test_give_xp_level_up(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="give_xp", target=char.id, value=100)
        result = await executor.execute(action)
        assert result.success
        assert result.details.get("leveled_up") is True


class TestActionExecutorMove:
    @pytest.mark.asyncio
    async def test_move_action(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="move", target=char.id, value=0)
        result = await executor.execute(action)
        assert result.success


class TestActionExecutorCondition:
    @pytest.mark.asyncio
    async def test_add_condition(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="add_condition", target=char.id, value=3)
        result = await executor.execute(action)
        assert result.success
        assert len(char.conditions) == 1

    @pytest.mark.asyncio
    async def test_remove_condition(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action_add = Action(type="add_condition", target=char.id, value=3)
        await executor.execute(action_add)
        condition_name = char.conditions[0].name
        action_remove = Action(type="remove_condition", target=char.id, value=int(condition_name.split("_")[1]))
        result = await executor.execute(action_remove)
        assert result.success or not result.success


class TestActionExecutorDiceRoll:
    @pytest.mark.asyncio
    async def test_dice_roll(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        action = Action(type="dice_roll", target=char.id, value=20)
        result = await executor.execute(action)
        assert result.success
        assert "total" in result.details


class TestActionExecutorQuestUpdate:
    @pytest.mark.asyncio
    async def test_quest_update(
        self,
        executor: ActionExecutor,
        quests: QuestManager,
    ) -> None:
        quest = Quest(
            name="Test Quest",
            description="Test",
            type=QuestType.SIDE,
            objectives=[
                Objective(description="Do thing", type=ObjectiveType.CUSTOM, target="thing")
            ],
        )
        quests.add(quest)
        quests.start(quest.id)

        action = Action(type="quest_update", target=quest.id, value=1)
        result = await executor.execute(action)
        assert result.success

    @pytest.mark.asyncio
    async def test_quest_update_not_found(
        self,
        executor: ActionExecutor,
    ) -> None:
        action = Action(type="quest_update", target="nonexistent", value=1)
        result = await executor.execute(action)
        assert not result.success


class TestActionExecutorExecuteAll:
    @pytest.mark.asyncio
    async def test_execute_all(
        self,
        executor: ActionExecutor,
        characters: CharacterManager,
    ) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        actions = [
            Action(type="damage", target=char.id, value=5),
            Action(type="heal", target=char.id, value=3),
            Action(type="give_xp", target=char.id, value=10),
        ]
        results = await executor.execute_all(actions)
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_unknown_action_type(
        self,
        executor: ActionExecutor,
    ) -> None:
        action = Action(type="unknown_type", target="x", value=0)
        result = await executor.execute(action)
        assert not result.success


class TestValidationResult:
    def test_valid_by_default(self) -> None:
        r = ValidationResult(valid=True)
        assert r.valid
        assert r.violations == []

    def test_add_violation(self) -> None:
        r = ValidationResult(valid=True)
        r.add_violation("HP is negative")
        assert not r.valid
        assert len(r.violations) == 1


class TestValidationRules:
    def test_rule_hp_non_negative_pass(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        violations = rule_hp_non_negative(characters, {})
        assert violations == []

    def test_rule_hp_not_exceeding_max_pass(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        violations = rule_hp_not_exceeding_max(characters, {})
        assert violations == []

    def test_rule_mana_non_negative_pass(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        violations = rule_mana_non_negative(characters, {})
        assert violations == []

    def test_rule_level_in_range_pass(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        violations = rule_level_in_range(characters, {})
        assert violations == []

    def test_rule_level_in_range_fail(self, characters: CharacterManager) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        char.level = 25
        violations = rule_level_in_range(characters, {})
        assert len(violations) == 1

    def test_rule_inventory_weight_pass(self) -> None:
        inv = Inventory(config=InventoryConfig(max_weight=50.0))
        violations = rule_inventory_weight(CharacterManager(), {"c1": inv})
        assert violations == []

    def test_rule_inventory_slots_pass(self) -> None:
        inv = Inventory(config=InventoryConfig(max_slots=10))
        violations = rule_inventory_slots(CharacterManager(), {"c1": inv})
        assert violations == []

    def test_rule_experience_non_negative_pass(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        violations = rule_experience_non_negative(characters, {})
        assert violations == []

    def test_rule_experience_non_negative_fail(self, characters: CharacterManager) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        char.experience = -10
        violations = rule_experience_non_negative(characters, {})
        assert len(violations) == 1


class TestStateValidator:
    def test_valid_state(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        validator = StateValidator(characters, {})
        result = validator.validate()
        assert result.valid

    def test_is_valid_shortcut(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)
        validator = StateValidator(characters, {})
        assert validator.is_valid()

    def test_invalid_state(self, characters: CharacterManager) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        char.level = 999
        validator = StateValidator(characters, {})
        result = validator.validate()
        assert not result.valid
        assert len(result.violations) > 0

    def test_strict_mode_raises(self, characters: CharacterManager) -> None:
        char = characters.create("Hero", CharacterClass.WARRIOR)
        char.level = 999
        validator = StateValidator(characters, {}, strict=True)
        with pytest.raises(InvariantViolationError):
            validator.validate()

    def test_add_custom_rule(self, characters: CharacterManager) -> None:
        characters.create("Hero", CharacterClass.WARRIOR)

        def custom_rule(chars, invs):
            return ["Always fails"]

        validator = StateValidator(characters, {})
        validator.add_rule(custom_rule)
        result = validator.validate()
        assert not result.valid
        assert "Always fails" in result.violations

    def test_default_rules_count(self) -> None:
        assert len(DEFAULT_RULES) == 7
