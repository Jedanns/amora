from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.combat.models import (
    CombatAction,
    CombatActionType,
    Combatant,
    CombatLogEntry,
    CombatState,
    CombatStatus,
    DamageType,
    TerrainModifiers,
)
from src.core.config import CombatConfig
from src.core.dice import DiceResult, DiceRoller, RollContext
from src.core.events import EventBus, EventType, GameEvent
from src.core.exceptions import StateError, ValidationError

if TYPE_CHECKING:
    from src.character.manager import CharacterManager
    from src.character.models import Character

logger = structlog.get_logger(__name__)

BASE_AC = 10
FLEE_DC = 12
CRITICAL_HIT_THRESHOLD = 20
CRITICAL_MISS_THRESHOLD = 1


def compute_armor_class(character: Character) -> int:
    dex_mod = character.attributes.get_modifier("dexterity")
    return BASE_AC + dex_mod


def compute_attack_bonus(character: Character) -> int:
    str_mod = character.attributes.get_modifier("strength")
    return str_mod


def compute_damage(
    character: Character,
    config: CombatConfig,
    roll: DiceResult,
    is_critical: bool = False,
) -> int:
    str_mod = character.attributes.get_modifier("strength")
    base = roll.total + str_mod
    if is_critical:
        base = int(base * config.critical_multiplier)
    return max(config.minimum_damage, base)


class CombatManager:
    def __init__(
        self,
        dice: DiceRoller,
        characters: CharacterManager,
        events: EventBus | None = None,
        config: CombatConfig | None = None,
    ) -> None:
        self._dice = dice
        self._characters = characters
        self._events = events or EventBus()
        self._config = config or CombatConfig()
        self._combat: CombatState | None = None

    @property
    def combat(self) -> CombatState | None:
        return self._combat

    @property
    def active_combat(self) -> CombatState:
        if self._combat is None or self._combat.is_finished:
            raise StateError("No active combat")
        return self._combat

    async def start_combat(
        self,
        participant_ids: list[str],
        teams: dict[str, str] | None = None,
        terrain: TerrainModifiers | None = None,
    ) -> CombatState:
        if len(participant_ids) < 2:
            raise ValidationError("Combat requires at least 2 participants")

        if self._combat and not self._combat.is_finished:
            raise StateError("A combat is already in progress")

        team_map = teams or {}
        combatants: list[Combatant] = []

        for char_id in participant_ids:
            character = self._characters.get(char_id)
            if not character.is_alive:
                raise ValidationError(
                    f"Character {char_id} is dead and cannot participate in combat"
                )

            initiative_roll = self._dice.roll(
                "1d20",
                RollContext(
                    reason="initiative",
                    actor_id=char_id,
                ),
            )
            dex_mod = character.attributes.get_modifier("dexterity")
            initiative = initiative_roll.total + dex_mod

            combatant = Combatant(
                character_id=char_id,
                team=team_map.get(char_id, "player" if not character.is_npc else "enemy"),
                initiative=initiative,
                actions_per_turn=self._config.actions_per_turn,
                actions_remaining=self._config.actions_per_turn,
            )
            combatants.append(combatant)

        combatants.sort(key=lambda c: c.initiative, reverse=True)
        turn_order = [c.character_id for c in combatants]

        self._combat = CombatState(
            participants=combatants,
            turn_order=turn_order,
            terrain=terrain,
            status=CombatStatus.ACTIVE,
        )

        await self._events.emit(
            GameEvent(
                type=EventType.COMBAT_STARTED,
                data={
                    "combat_id": self._combat.id,
                    "participants": participant_ids,
                    "turn_order": turn_order,
                },
                source="combat_manager",
            )
        )

        logger.info(
            "combat_started",
            combat_id=self._combat.id,
            participants=len(combatants),
            turn_order=turn_order,
        )

        return self._combat

    async def execute_action(self, action: CombatAction) -> CombatLogEntry:
        combat = self.active_combat

        if combat.current_combatant_id != action.actor_id:
            raise StateError(
                f"It is not {action.actor_id}'s turn. "
                f"Current: {combat.current_combatant_id}"
            )

        combatant = combat.get_combatant(action.actor_id)
        if combatant is None:
            raise ValidationError(f"Combatant not found: {action.actor_id}")

        if not combatant.can_act:
            raise StateError(
                f"{action.actor_id} cannot act (no actions remaining or incapacitated)"
            )

        handler = self._get_action_handler(action.type)
        log_entry = await handler(combat, combatant, action)

        combatant.actions_remaining -= 1
        combat.log.append(log_entry)

        self._check_combat_end(combat)

        return log_entry

    async def advance_turn(self) -> str | None:
        combat = self.active_combat

        combat.current_turn_index += 1

        if combat.current_turn_index >= len(combat.turn_order):
            combat.current_turn_index = 0
            combat.round += 1
            self._on_new_round(combat)

        self._skip_dead_combatants(combat)

        if combat.is_finished:
            return None

        current_id = combat.current_combatant_id
        if current_id:
            combatant = combat.get_combatant(current_id)
            if combatant:
                combatant.reset_turn()

        return current_id

    async def end_combat(
        self, status: CombatStatus = CombatStatus.DRAW
    ) -> CombatState:
        combat = self.active_combat
        combat.status = status

        await self._events.emit(
            GameEvent(
                type=EventType.COMBAT_ENDED,
                data={
                    "combat_id": combat.id,
                    "status": status.value,
                    "rounds": combat.round,
                    "log_entries": len(combat.log),
                },
                source="combat_manager",
            )
        )

        logger.info(
            "combat_ended",
            combat_id=combat.id,
            status=status.value,
            rounds=combat.round,
        )

        return combat

    def _get_action_handler(self, action_type: CombatActionType):
        handlers = {
            CombatActionType.ATTACK: self._handle_attack,
            CombatActionType.DEFEND: self._handle_defend,
            CombatActionType.FLEE: self._handle_flee,
            CombatActionType.PASS_TURN: self._handle_pass,
            CombatActionType.USE_ITEM: self._handle_use_item,
            CombatActionType.CAST: self._handle_cast,
        }
        handler = handlers.get(action_type)
        if handler is None:
            raise ValidationError(f"Unknown action type: {action_type}")
        return handler

    async def _handle_attack(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        if not action.target_id:
            raise ValidationError("Attack requires a target")

        target = combat.get_combatant(action.target_id)
        if target is None:
            raise ValidationError(f"Target not found: {action.target_id}")

        target_char = self._characters.get(action.target_id)
        if not target_char.is_alive:
            raise ValidationError(f"Target {action.target_id} is already dead")

        attacker_char = self._characters.get(action.actor_id)

        attack_bonus = compute_attack_bonus(attacker_char) + combatant.total_attack_modifier
        target_ac = compute_armor_class(target_char) + target.total_defense_modifier

        if combat.terrain:
            attack_bonus -= combat.terrain.attack_penalty
            target_ac += combat.terrain.defense_bonus

        attack_roll = self._dice.roll(
            "1d20",
            RollContext(
                reason="attack",
                actor_id=action.actor_id,
                target_id=action.target_id,
            ),
        )

        raw_roll = attack_roll.total
        total_attack = raw_roll + attack_bonus

        is_critical = raw_roll >= CRITICAL_HIT_THRESHOLD
        is_fumble = raw_roll <= CRITICAL_MISS_THRESHOLD

        hit = is_critical or (not is_fumble and total_attack >= target_ac)

        damage_dealt = 0
        if hit:
            damage_notation = self._config.base_damage_dice
            damage_roll = self._dice.roll(
                damage_notation,
                RollContext(
                    reason="damage",
                    actor_id=action.actor_id,
                    target_id=action.target_id,
                ),
            )
            damage_dealt = compute_damage(
                attacker_char,
                self._config,
                damage_roll,
                is_critical=is_critical,
            )
            damage_dealt += combatant.total_damage_modifier
            damage_dealt = max(self._config.minimum_damage, damage_dealt)

            self._characters.apply_damage(action.target_id, damage_dealt)

        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.ATTACK,
            target_id=action.target_id,
            roll_result=total_attack,
            roll_target=target_ac,
            hit=hit,
            damage_dealt=damage_dealt,
            damage_type=DamageType.PHYSICAL,
        )

    async def _handle_defend(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        combatant.is_defending = True

        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.DEFEND,
        )

    async def _handle_flee(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        character = self._characters.get(action.actor_id)
        dex_mod = character.attributes.get_modifier("dexterity")

        flee_roll = self._dice.roll(
            "1d20",
            RollContext(reason="flee", actor_id=action.actor_id),
        )
        total = flee_roll.total + dex_mod
        success = total >= FLEE_DC

        if success:
            combat.status = CombatStatus.FLED

        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.FLEE,
            roll_result=total,
            roll_target=FLEE_DC,
            hit=success,
        )

    async def _handle_pass(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.PASS_TURN,
        )

    async def _handle_use_item(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.USE_ITEM,
            target_id=action.target_id,
        )

    async def _handle_cast(
        self,
        combat: CombatState,
        combatant: Combatant,
        action: CombatAction,
    ) -> CombatLogEntry:
        character = self._characters.get(action.actor_id)
        int_mod = character.attributes.get_modifier("intelligence")

        if character.mana.is_depleted:
            raise StateError(f"{action.actor_id} has no mana to cast spells")

        mana_cost = max(1, 5 - int_mod)
        actual_cost = min(mana_cost, character.mana.current)
        character.mana.apply_damage(actual_cost)

        damage_dealt = 0
        hit = None

        if action.target_id:
            target = combat.get_combatant(action.target_id)
            if target is None:
                raise ValidationError(f"Target not found: {action.target_id}")

            target_char = self._characters.get(action.target_id)
            spell_roll = self._dice.roll(
                "1d20",
                RollContext(
                    reason="spell_attack",
                    actor_id=action.actor_id,
                    target_id=action.target_id,
                ),
            )
            spell_dc = BASE_AC + target_char.attributes.get_modifier("wisdom")
            total = spell_roll.total + int_mod
            hit = total >= spell_dc

            if hit:
                damage_roll = self._dice.roll(
                    self._config.spell_damage_dice,
                    RollContext(
                        reason="spell_damage",
                        actor_id=action.actor_id,
                        target_id=action.target_id,
                    ),
                )
                damage_dealt = max(
                    self._config.minimum_damage,
                    damage_roll.total + int_mod,
                )
                self._characters.apply_damage(action.target_id, damage_dealt)

        return CombatLogEntry(
            round=combat.round,
            turn=combat.current_turn_index,
            actor_id=action.actor_id,
            action_type=CombatActionType.CAST,
            target_id=action.target_id,
            roll_result=spell_roll.total + int_mod if action.target_id else None,
            roll_target=spell_dc if action.target_id else None,
            hit=hit,
            damage_dealt=damage_dealt,
            damage_type=DamageType.MAGICAL,
        )

    def _on_new_round(self, combat: CombatState) -> None:
        for combatant in combat.participants:
            expired = combatant.tick_conditions()
            if expired:
                logger.debug(
                    "combat_conditions_expired",
                    character_id=combatant.character_id,
                    expired=expired,
                )

            for condition in combatant.conditions:
                if condition.damage_per_round > 0:
                    char = self._characters.get(combatant.character_id)
                    if char.is_alive:
                        self._characters.apply_damage(
                            combatant.character_id,
                            condition.damage_per_round,
                        )

        if combat.round > self._config.max_rounds:
            combat.status = CombatStatus.DRAW

    def _skip_dead_combatants(self, combat: CombatState) -> None:
        if combat.is_finished:
            return

        checked = 0
        while checked < len(combat.turn_order):
            current_id = combat.current_combatant_id
            if current_id is None:
                break

            char = self._characters.get(current_id)
            if char.is_alive:
                break

            combat.current_turn_index += 1
            if combat.current_turn_index >= len(combat.turn_order):
                combat.current_turn_index = 0
                combat.round += 1
                self._on_new_round(combat)
                if combat.is_finished:
                    break

            checked += 1

    def _check_combat_end(self, combat: CombatState) -> None:
        teams = combat.get_teams()
        alive_teams: list[str] = []

        for team_name, members in teams.items():
            has_alive = any(
                self._characters.get(m.character_id).is_alive
                for m in members
            )
            if has_alive:
                alive_teams.append(team_name)

        if len(alive_teams) <= 1:
            if not alive_teams:
                combat.status = CombatStatus.DRAW
            elif alive_teams[0] == "player":
                combat.status = CombatStatus.VICTORY
            else:
                combat.status = CombatStatus.DEFEAT
