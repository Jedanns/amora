import pytest

from src.combat.models import (
    CombatAction,
    CombatActionType,
    Combatant,
    CombatCondition,
    CombatLogEntry,
    CombatState,
    CombatStatus,
    Position2D,
    TerrainModifiers,
    TerrainType,
)


class TestPosition2D:
    def test_distance_to_same(self) -> None:
        p = Position2D(x=0, y=0)
        assert p.distance_to(p) == 0.0

    def test_distance_to_other(self) -> None:
        p1 = Position2D(x=0, y=0)
        p2 = Position2D(x=3, y=4)
        assert p1.distance_to(p2) == pytest.approx(5.0)

    def test_is_adjacent_true(self) -> None:
        p1 = Position2D(x=0, y=0)
        p2 = Position2D(x=1, y=1)
        assert p1.is_adjacent(p2)

    def test_is_adjacent_false(self) -> None:
        p1 = Position2D(x=0, y=0)
        p2 = Position2D(x=3, y=3)
        assert not p1.is_adjacent(p2)

    def test_is_adjacent_custom_range(self) -> None:
        p1 = Position2D(x=0, y=0)
        p2 = Position2D(x=2, y=2)
        assert p1.is_adjacent(p2, range_=2)


class TestTerrainModifiers:
    def test_defaults(self) -> None:
        t = TerrainModifiers()
        assert t.type == TerrainType.OPEN
        assert t.defense_bonus == 0
        assert t.attack_penalty == 0
        assert t.movement_cost == 1.0

    def test_custom_terrain(self) -> None:
        t = TerrainModifiers(
            type=TerrainType.FOREST,
            defense_bonus=2,
            attack_penalty=1,
            movement_cost=1.5,
        )
        assert t.type == TerrainType.FOREST
        assert t.defense_bonus == 2


class TestCombatCondition:
    def test_tick_permanent(self) -> None:
        c = CombatCondition(name="blessed")
        assert not c.tick()

    def test_tick_expires(self) -> None:
        c = CombatCondition(name="stunned", remaining_rounds=1)
        assert c.tick()

    def test_tick_decrements(self) -> None:
        c = CombatCondition(name="burning", remaining_rounds=3)
        assert not c.tick()
        assert c.remaining_rounds == 2

    def test_modifiers(self) -> None:
        c = CombatCondition(
            name="weakened",
            attack_modifier=-2,
            defense_modifier=-1,
            damage_modifier=-1,
        )
        assert c.attack_modifier == -2
        assert c.defense_modifier == -1


class TestCombatant:
    def test_can_act_with_actions(self) -> None:
        c = Combatant(character_id="char_1", actions_remaining=1)
        assert c.can_act

    def test_cannot_act_no_actions(self) -> None:
        c = Combatant(character_id="char_1", actions_remaining=0)
        assert not c.can_act

    def test_cannot_act_incapacitated(self) -> None:
        c = Combatant(
            character_id="char_1",
            actions_remaining=1,
            conditions=[CombatCondition(name="stunned", prevents_action=True)],
        )
        assert not c.can_act

    def test_total_modifiers(self) -> None:
        c = Combatant(
            character_id="char_1",
            conditions=[
                CombatCondition(name="blessed", attack_modifier=2, defense_modifier=1),
                CombatCondition(name="weakened", attack_modifier=-1, damage_modifier=-2),
            ],
        )
        assert c.total_attack_modifier == 1
        assert c.total_defense_modifier == 1
        assert c.total_damage_modifier == -2

    def test_defense_with_defending(self) -> None:
        c = Combatant(character_id="char_1", is_defending=True)
        assert c.total_defense_modifier == 2

    def test_reset_turn(self) -> None:
        c = Combatant(
            character_id="char_1",
            actions_per_turn=2,
            actions_remaining=0,
            is_defending=True,
        )
        c.reset_turn()
        assert c.actions_remaining == 2
        assert not c.is_defending

    def test_tick_conditions(self) -> None:
        c = Combatant(
            character_id="char_1",
            conditions=[
                CombatCondition(name="burning", remaining_rounds=1),
                CombatCondition(name="blessed"),
            ],
        )
        expired = c.tick_conditions()
        assert expired == ["burning"]
        assert len(c.conditions) == 1
        assert c.conditions[0].name == "blessed"


class TestCombatLogEntry:
    def test_narrative_string_hit(self) -> None:
        entry = CombatLogEntry(
            round=1,
            turn=0,
            actor_id="hero",
            action_type=CombatActionType.ATTACK,
            target_id="goblin",
            roll_result=18,
            roll_target=12,
            hit=True,
            damage_dealt=8,
        )
        text = entry.to_narrative_string()
        assert "hero" in text
        assert "8" in text

    def test_narrative_string_miss(self) -> None:
        entry = CombatLogEntry(
            round=1,
            turn=0,
            actor_id="hero",
            action_type=CombatActionType.ATTACK,
            target_id="goblin",
            hit=False,
        )
        text = entry.to_narrative_string()
        assert "miss" in text

    def test_custom_narrative(self) -> None:
        entry = CombatLogEntry(
            round=1,
            turn=0,
            actor_id="hero",
            action_type=CombatActionType.ATTACK,
            narrative="The hero strikes with fury!",
        )
        assert entry.to_narrative_string() == "The hero strikes with fury!"


class TestCombatAction:
    def test_basic_action(self) -> None:
        a = CombatAction(
            type=CombatActionType.ATTACK,
            actor_id="char_1",
            target_id="char_2",
        )
        assert a.type == CombatActionType.ATTACK
        assert a.actor_id == "char_1"
        assert a.target_id == "char_2"


class TestCombatState:
    def test_initial_state(self) -> None:
        state = CombatState()
        assert state.status == CombatStatus.PENDING
        assert state.round == 1
        assert state.current_turn_index == 0
        assert not state.is_finished

    def test_current_combatant_id(self) -> None:
        state = CombatState(
            turn_order=["char_a", "char_b", "char_c"],
            current_turn_index=1,
        )
        assert state.current_combatant_id == "char_b"

    def test_current_combatant_empty(self) -> None:
        state = CombatState()
        assert state.current_combatant_id is None

    def test_current_combatant_out_of_bounds(self) -> None:
        state = CombatState(
            turn_order=["char_a"],
            current_turn_index=5,
        )
        assert state.current_combatant_id is None

    def test_is_finished_active(self) -> None:
        state = CombatState(status=CombatStatus.ACTIVE)
        assert not state.is_finished

    def test_is_finished_victory(self) -> None:
        state = CombatState(status=CombatStatus.VICTORY)
        assert state.is_finished

    def test_is_finished_defeat(self) -> None:
        state = CombatState(status=CombatStatus.DEFEAT)
        assert state.is_finished

    def test_is_finished_fled(self) -> None:
        state = CombatState(status=CombatStatus.FLED)
        assert state.is_finished

    def test_get_combatant(self) -> None:
        c = Combatant(character_id="char_1")
        state = CombatState(participants=[c])
        assert state.get_combatant("char_1") is c
        assert state.get_combatant("char_999") is None

    def test_get_teams(self) -> None:
        state = CombatState(
            participants=[
                Combatant(character_id="p1", team="player"),
                Combatant(character_id="p2", team="player"),
                Combatant(character_id="e1", team="enemy"),
            ]
        )
        teams = state.get_teams()
        assert len(teams["player"]) == 2
        assert len(teams["enemy"]) == 1

    def test_to_context_string(self) -> None:
        state = CombatState(
            participants=[
                Combatant(character_id="hero", team="player", initiative=15),
                Combatant(character_id="goblin", team="enemy", initiative=10),
            ],
            turn_order=["hero", "goblin"],
            status=CombatStatus.ACTIVE,
        )
        text = state.to_context_string()
        assert "active" in text.lower()
        assert "hero" in text
        assert "goblin" in text


class TestCombatStatus:
    def test_is_finished_variants(self) -> None:
        assert CombatStatus.VICTORY.is_finished
        assert CombatStatus.DEFEAT.is_finished
        assert CombatStatus.FLED.is_finished
        assert CombatStatus.DRAW.is_finished
        assert not CombatStatus.ACTIVE.is_finished
        assert not CombatStatus.PENDING.is_finished
        assert not CombatStatus.PAUSED.is_finished
