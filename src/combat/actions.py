from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from src.character.models import Condition, ConditionType, DurationType
from src.core.dice import DiceRoller, RollContext
from src.core.events import EventBus, EventType, GameEvent
from src.core.exceptions import CharacterError, ValidationError
from src.inventory.item import Item
from src.llm.parser import Action, ActionType

if TYPE_CHECKING:
    from src.character.manager import CharacterManager
    from src.inventory.manager import Inventory
    from src.quest.manager import QuestManager

logger = structlog.get_logger(__name__)


@dataclass
class ActionResult:
    action: Action
    success: bool
    message: str = ""
    details: dict[str, object] = field(default_factory=dict)


class ActionExecutor:
    def __init__(
        self,
        characters: CharacterManager,
        inventories: dict[str, Inventory],
        quests: QuestManager,
        dice: DiceRoller,
        events: EventBus | None = None,
    ) -> None:
        self._characters = characters
        self._inventories = inventories
        self._quests = quests
        self._dice = dice
        self._events = events or EventBus()

    async def execute(self, action: Action) -> ActionResult:
        handler = self._get_handler(action.action_type)
        if handler is None:
            return ActionResult(
                action=action,
                success=False,
                message=f"No handler for action type: {action.type}",
            )

        try:
            result = await handler(action)
            logger.info(
                "action_executed",
                type=action.type,
                target=action.target,
                value=action.value,
                success=result.success,
            )
            return result
        except (ValidationError, CharacterError) as e:
            logger.warning(
                "action_failed",
                type=action.type,
                target=action.target,
                error=str(e),
            )
            return ActionResult(
                action=action,
                success=False,
                message=str(e),
            )

    async def execute_all(self, actions: list[Action]) -> list[ActionResult]:
        results: list[ActionResult] = []
        for action in actions:
            result = await self.execute(action)
            results.append(result)
        return results

    def _get_handler(self, action_type: ActionType):
        handlers = {
            ActionType.DAMAGE: self._handle_damage,
            ActionType.HEAL: self._handle_heal,
            ActionType.GIVE_ITEM: self._handle_give_item,
            ActionType.REMOVE_ITEM: self._handle_remove_item,
            ActionType.GIVE_XP: self._handle_give_xp,
            ActionType.MOVE: self._handle_move,
            ActionType.ADD_CONDITION: self._handle_add_condition,
            ActionType.REMOVE_CONDITION: self._handle_remove_condition,
            ActionType.DICE_ROLL: self._handle_dice_roll,
            ActionType.QUEST_UPDATE: self._handle_quest_update,
        }
        return handlers.get(action_type)

    async def _handle_damage(self, action: Action) -> ActionResult:
        if action.value < 0:
            raise ValidationError(f"Damage value must be non-negative: {action.value}")

        actual = self._characters.apply_damage(action.target, action.value)

        await self._events.emit(
            GameEvent(
                type=EventType.CHARACTER_UPDATED,
                data={
                    "character_id": action.target,
                    "change": "damage",
                    "amount": actual,
                },
                source="action_executor",
            )
        )

        return ActionResult(
            action=action,
            success=True,
            message=f"Dealt {actual} damage to {action.target}",
            details={"actual_damage": actual},
        )

    async def _handle_heal(self, action: Action) -> ActionResult:
        if action.value < 0:
            raise ValidationError(f"Heal value must be non-negative: {action.value}")

        actual = self._characters.apply_heal(action.target, action.value)

        await self._events.emit(
            GameEvent(
                type=EventType.CHARACTER_UPDATED,
                data={
                    "character_id": action.target,
                    "change": "heal",
                    "amount": actual,
                },
                source="action_executor",
            )
        )

        return ActionResult(
            action=action,
            success=True,
            message=f"Healed {action.target} for {actual} HP",
            details={"actual_heal": actual},
        )

    async def _handle_give_item(self, action: Action) -> ActionResult:
        inventory = self._inventories.get(action.target)
        if inventory is None:
            return ActionResult(
                action=action,
                success=False,
                message=f"No inventory for character: {action.target}",
            )

        item = Item(
            name=f"item_{action.value}",
            description=f"Generated item (value: {action.value})",
        )
        inventory.add(item)

        await self._events.emit(
            GameEvent(
                type=EventType.ITEM_ADDED,
                data={
                    "character_id": action.target,
                    "item_id": item.id,
                    "item_name": item.name,
                },
                source="action_executor",
            )
        )

        return ActionResult(
            action=action,
            success=True,
            message=f"Gave {item.name} to {action.target}",
            details={"item_id": item.id},
        )

    async def _handle_remove_item(self, action: Action) -> ActionResult:
        inventory = self._inventories.get(action.target)
        if inventory is None:
            return ActionResult(
                action=action,
                success=False,
                message=f"No inventory for character: {action.target}",
            )

        items = inventory.items
        if not items:
            return ActionResult(
                action=action,
                success=False,
                message=f"Inventory of {action.target} is empty",
            )

        target_item = None
        for item in items:
            if item.id == str(action.value) or item.name == str(action.value):
                target_item = item
                break

        if target_item is None and items:
            target_item = items[0]

        if target_item:
            inventory.remove(target_item.id)

            await self._events.emit(
                GameEvent(
                    type=EventType.ITEM_REMOVED,
                    data={
                        "character_id": action.target,
                        "item_id": target_item.id,
                    },
                    source="action_executor",
                )
            )

            return ActionResult(
                action=action,
                success=True,
                message=f"Removed {target_item.name} from {action.target}",
                details={"item_id": target_item.id},
            )

        return ActionResult(
            action=action,
            success=False,
            message="No item to remove",
        )

    async def _handle_give_xp(self, action: Action) -> ActionResult:
        if action.value < 0:
            raise ValidationError(f"XP value must be non-negative: {action.value}")

        leveled = self._characters.add_experience(action.target, action.value)

        return ActionResult(
            action=action,
            success=True,
            message=f"Gave {action.value} XP to {action.target}"
            + (" (LEVEL UP!)" if leveled else ""),
            details={"leveled_up": leveled},
        )

    async def _handle_move(self, action: Action) -> ActionResult:
        location = str(action.value) if action.value else action.target
        character = self._characters.get(action.target)
        old_location = character.location
        self._characters.move(action.target, location)

        return ActionResult(
            action=action,
            success=True,
            message=f"Moved {action.target} from {old_location} to {location}",
            details={"old_location": old_location, "new_location": location},
        )

    async def _handle_add_condition(self, action: Action) -> ActionResult:
        character = self._characters.get(action.target)

        condition = Condition(
            name=f"condition_{action.value}",
            type=ConditionType.BUFF if action.value > 0 else ConditionType.DEBUFF,
            duration_type=DurationType.ROUNDS,
            remaining=abs(action.value),
        )
        character.add_condition(condition)

        await self._events.emit(
            GameEvent(
                type=EventType.CONDITION_APPLIED,
                data={
                    "character_id": action.target,
                    "condition_name": condition.name,
                },
                source="action_executor",
            )
        )

        return ActionResult(
            action=action,
            success=True,
            message=f"Applied {condition.name} to {action.target} "
            f"for {condition.remaining} rounds",
            details={"condition_id": condition.id},
        )

    async def _handle_remove_condition(self, action: Action) -> ActionResult:
        character = self._characters.get(action.target)
        condition_name = str(action.value)
        removed = character.remove_condition(condition_name)

        if removed:
            await self._events.emit(
                GameEvent(
                    type=EventType.CONDITION_REMOVED,
                    data={
                        "character_id": action.target,
                        "condition_name": condition_name,
                    },
                    source="action_executor",
                )
            )

        return ActionResult(
            action=action,
            success=removed,
            message=f"Removed {condition_name} from {action.target}"
            if removed
            else f"Condition {condition_name} not found on {action.target}",
        )

    async def _handle_dice_roll(self, action: Action) -> ActionResult:
        notation = f"1d{action.value}" if action.value in {4, 6, 8, 10, 12, 20, 100} else "1d20"
        result = self._dice.roll(
            notation,
            RollContext(reason="llm_action", actor_id=action.target),
        )

        return ActionResult(
            action=action,
            success=True,
            message=f"Rolled {notation} = {result.total}",
            details={"roll_id": result.id, "total": result.total},
        )

    async def _handle_quest_update(self, action: Action) -> ActionResult:
        quest_id = action.target
        progress = action.value

        try:
            quest = self._quests.get(quest_id)
        except Exception:
            return ActionResult(
                action=action,
                success=False,
                message=f"Quest not found: {quest_id}",
            )

        if quest.objectives:
            obj = quest.objectives[0]
            self._quests.advance_objective(quest_id, obj.id, progress)

        return ActionResult(
            action=action,
            success=True,
            message=f"Updated quest {quest_id} progress by {progress}",
            details={"quest_id": quest_id},
        )
