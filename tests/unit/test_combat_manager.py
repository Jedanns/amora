import pytest

from src.character.manager import CharacterManager
from src.character.models import Attributes, CharacterClass
from src.combat.manager import (
    BASE_AC,
    CombatManager,
    compute_armor_class,
    compute_attack_bonus,
    compute_damage,
)
from src.combat.models import (
    CombatAction,
    CombatActionType,
    CombatStatus,
    DamageType,
    TerrainModifiers,
    TerrainType,
)
from src.core.config import CombatConfig
from src.core.dice import DiceRoller
from src.core.events import EventBus, EventType
from src.core.exceptions import StateError, ValidationError


@pytest.fixture
def combat_config() -> CombatConfig:
    return CombatConfig()


@pytest.fixture
def events() -> EventBus:
    return EventBus()


@pytest.fixture
def characters() -> CharacterManager:
    return CharacterManager()


@pytest.fixture
def dice() -> DiceRoller:
    return DiceRoller(seed=42)


@pytest.fixture
def combat_manager(
    dice: DiceRoller,
    characters: CharacterManager,
    events: EventBus,
    combat_config: CombatConfig,
) -> CombatManager:
    return CombatManager(dice, characters, events, combat_config)


@pytest.fixture
def two_fighters(characters: CharacterManager) -> tuple[str, str]:
    hero = characters.create("Hero", CharacterClass.WARRIOR, player_id="p1")
    enemy = characters.create("Goblin", CharacterClass.ROGUE)
    return hero.id, enemy.id


class TestComputeFunctions:
    def test_compute_armor_class_default(self, characters: CharacterManager) -> None:
        char = characters.create("Test", CharacterClass.WARRIOR)
        ac = compute_armor_class(char)
        assert ac == BASE_AC + char.attributes.get_modifier("dexterity")

    def test_compute_armor_class_high_dex(self, characters: CharacterManager) -> None:
        char = characters.create("Test", CharacterClass.ROGUE)
        char.attributes = Attributes(dexterity=18)
        ac = compute_armor_class(char)
        assert ac == BASE_AC + 4

    def test_compute_attack_bonus(self, characters: CharacterManager) -> None:
        char = characters.create("Test", CharacterClass.WARRIOR)
        char.attributes = Attributes(strength=16)
        bonus = compute_attack_bonus(char)
        assert bonus == 3

    def test_compute_damage_normal(self, characters: CharacterManager) -> None:
        char = characters.create("Test", CharacterClass.WARRIOR)
        char.attributes = Attributes(strength=14)
        config = CombatConfig()
        roll = DiceRoller(seed=42).roll("1d6")
        damage = compute_damage(char, config, roll, is_critical=False)
        assert damage >= config.minimum_damage

    def test_compute_damage_critical(self, characters: CharacterManager) -> None:
        char = characters.create("Test", CharacterClass.WARRIOR)
        char.attributes = Attributes(strength=14)
        config = CombatConfig(critical_multiplier=2.0)
        roll = DiceRoller(seed=42).roll("1d6")
        normal = compute_damage(char, config, roll, is_critical=False)
        crit = compute_damage(char, config, roll, is_critical=True)
        assert crit >= normal


class TestCombatManagerStartCombat:
    @pytest.mark.asyncio
    async def test_start_combat_success(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        assert combat.status == CombatStatus.ACTIVE
        assert len(combat.participants) == 2
        assert len(combat.turn_order) == 2

    @pytest.mark.asyncio
    async def test_start_combat_too_few(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, _ = two_fighters
        with pytest.raises(ValidationError):
            await combat_manager.start_combat([hero_id])

    @pytest.mark.asyncio
    async def test_start_combat_already_active(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        await combat_manager.start_combat([hero_id, enemy_id])
        with pytest.raises(StateError):
            await combat_manager.start_combat([hero_id, enemy_id])

    @pytest.mark.asyncio
    async def test_start_combat_dead_character(
        self,
        combat_manager: CombatManager,
        characters: CharacterManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        characters.apply_damage(enemy_id, 9999)
        with pytest.raises(ValidationError, match="dead"):
            await combat_manager.start_combat([hero_id, enemy_id])

    @pytest.mark.asyncio
    async def test_start_combat_with_teams(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        teams = {hero_id: "party", enemy_id: "monsters"}
        combat = await combat_manager.start_combat(
            [hero_id, enemy_id], teams=teams
        )
        hero_combatant = combat.get_combatant(hero_id)
        assert hero_combatant is not None
        assert hero_combatant.team == "party"

    @pytest.mark.asyncio
    async def test_start_combat_with_terrain(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        terrain = TerrainModifiers(type=TerrainType.FOREST, defense_bonus=2)
        combat = await combat_manager.start_combat(
            [hero_id, enemy_id], terrain=terrain
        )
        assert combat.terrain is not None
        assert combat.terrain.type == TerrainType.FOREST

    @pytest.mark.asyncio
    async def test_initiative_order(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        initiatives = [
            p.initiative for p in combat.participants
        ]
        assert initiatives == sorted(initiatives, reverse=True)


class TestCombatManagerAttack:
    @pytest.mark.asyncio
    async def test_attack_hit_or_miss(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None
        other = enemy_id if current == hero_id else hero_id

        action = CombatAction(
            type=CombatActionType.ATTACK,
            actor_id=current,
            target_id=other,
        )
        log = await combat_manager.execute_action(action)
        assert log.action_type == CombatActionType.ATTACK
        assert log.hit is not None

    @pytest.mark.asyncio
    async def test_attack_no_target(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        action = CombatAction(
            type=CombatActionType.ATTACK,
            actor_id=current,
        )
        with pytest.raises(ValidationError, match="target"):
            await combat_manager.execute_action(action)

    @pytest.mark.asyncio
    async def test_attack_wrong_turn(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        wrong_actor = enemy_id if current == hero_id else hero_id

        action = CombatAction(
            type=CombatActionType.ATTACK,
            actor_id=wrong_actor,
            target_id=current,
        )
        with pytest.raises(StateError, match="turn"):
            await combat_manager.execute_action(action)


class TestCombatManagerDefend:
    @pytest.mark.asyncio
    async def test_defend_sets_flag(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None

        action = CombatAction(
            type=CombatActionType.DEFEND,
            actor_id=current,
        )
        await combat_manager.execute_action(action)
        combatant = combat.get_combatant(current)
        assert combatant is not None
        assert combatant.is_defending


class TestCombatManagerFlee:
    @pytest.mark.asyncio
    async def test_flee_attempt(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None

        action = CombatAction(
            type=CombatActionType.FLEE,
            actor_id=current,
        )
        log = await combat_manager.execute_action(action)
        assert log.action_type == CombatActionType.FLEE
        assert log.hit is not None


class TestCombatManagerAdvanceTurn:
    @pytest.mark.asyncio
    async def test_advance_turn(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        first = combat.current_combatant_id

        action = CombatAction(
            type=CombatActionType.PASS_TURN,
            actor_id=first,
        )
        await combat_manager.execute_action(action)

        next_id = await combat_manager.advance_turn()
        assert next_id is not None
        assert next_id != first

    @pytest.mark.asyncio
    async def test_advance_wraps_round(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        assert combat.round == 1

        for _ in range(len(combat.turn_order)):
            current = combat.current_combatant_id
            if current:
                action = CombatAction(
                    type=CombatActionType.PASS_TURN,
                    actor_id=current,
                )
                await combat_manager.execute_action(action)
            await combat_manager.advance_turn()

        assert combat.round == 2


class TestCombatManagerEndCombat:
    @pytest.mark.asyncio
    async def test_end_combat(
        self,
        combat_manager: CombatManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        await combat_manager.start_combat([hero_id, enemy_id])
        result = await combat_manager.end_combat(CombatStatus.VICTORY)
        assert result.status == CombatStatus.VICTORY
        assert result.is_finished

    @pytest.mark.asyncio
    async def test_end_combat_no_active(
        self,
        combat_manager: CombatManager,
    ) -> None:
        with pytest.raises(StateError):
            await combat_manager.end_combat()

    @pytest.mark.asyncio
    async def test_auto_end_on_defeat(
        self,
        combat_manager: CombatManager,
        characters: CharacterManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None
        other = enemy_id if current == hero_id else hero_id

        characters.apply_damage(other, 9999)

        action = CombatAction(
            type=CombatActionType.PASS_TURN,
            actor_id=current,
        )
        await combat_manager.execute_action(action)
        assert combat.is_finished


class TestCombatManagerEvents:
    @pytest.mark.asyncio
    async def test_combat_started_event(
        self,
        combat_manager: CombatManager,
        events: EventBus,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        received: list[str] = []

        async def handler(event):
            received.append(event.type)

        events.subscribe(EventType.COMBAT_STARTED, handler)
        await combat_manager.start_combat([hero_id, enemy_id])
        assert "combat_started" in received

    @pytest.mark.asyncio
    async def test_combat_ended_event(
        self,
        combat_manager: CombatManager,
        events: EventBus,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        received: list[str] = []

        async def handler(event):
            received.append(event.type)

        events.subscribe(EventType.COMBAT_ENDED, handler)
        await combat_manager.start_combat([hero_id, enemy_id])
        await combat_manager.end_combat(CombatStatus.DRAW)
        assert "combat_ended" in received


class TestCombatManagerCast:
    @pytest.mark.asyncio
    async def test_cast_with_target(
        self,
        combat_manager: CombatManager,
        characters: CharacterManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        hero = characters.get(hero_id)
        hero.mana = hero.mana.model_copy(update={"current": 20, "max": 20})

        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None
        other = enemy_id if current == hero_id else hero_id

        caster = characters.get(current)
        caster.mana = caster.mana.model_copy(update={"current": 20, "max": 20})

        action = CombatAction(
            type=CombatActionType.CAST,
            actor_id=current,
            target_id=other,
        )
        log = await combat_manager.execute_action(action)
        assert log.action_type == CombatActionType.CAST
        assert log.damage_type == DamageType.MAGICAL

    @pytest.mark.asyncio
    async def test_cast_no_mana(
        self,
        combat_manager: CombatManager,
        characters: CharacterManager,
        two_fighters: tuple[str, str],
    ) -> None:
        hero_id, enemy_id = two_fighters
        combat = await combat_manager.start_combat([hero_id, enemy_id])
        current = combat.current_combatant_id
        assert current is not None
        other = enemy_id if current == hero_id else hero_id

        caster = characters.get(current)
        caster.mana.current = 0

        action = CombatAction(
            type=CombatActionType.CAST,
            actor_id=current,
            target_id=other,
        )
        with pytest.raises(StateError, match="mana"):
            await combat_manager.execute_action(action)
