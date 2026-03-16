import pytest

from src.character.manager import CharacterManager
from src.character.models import (
    Attributes,
    Character,
    CharacterClass,
    Condition,
    ConditionType,
    DurationType,
    StatPool,
)
from src.core.exceptions import CharacterError, ValidationError


class TestStatPool:
    def test_creation(self) -> None:
        pool = StatPool(current=20, max=20)
        assert pool.current == 20
        assert pool.max == 20
        assert pool.effective_max == 20

    def test_current_clamped_to_max(self) -> None:
        pool = StatPool(current=30, max=20)
        assert pool.current == 20

    def test_apply_damage(self) -> None:
        pool = StatPool(current=20, max=20)
        actual = pool.apply_damage(8)
        assert actual == 8
        assert pool.current == 12

    def test_apply_lethal_damage(self) -> None:
        pool = StatPool(current=10, max=20)
        pool.apply_damage(15)
        assert pool.current == 0
        assert pool.is_depleted

    def test_apply_heal(self) -> None:
        pool = StatPool(current=10, max=20)
        actual = pool.apply_heal(5)
        assert actual == 5
        assert pool.current == 15

    def test_heal_clamped_to_max(self) -> None:
        pool = StatPool(current=18, max=20)
        actual = pool.apply_heal(10)
        assert actual == 2
        assert pool.current == 20

    def test_temporary_max_increase(self) -> None:
        pool = StatPool(current=20, max=20, temporary_max_increase=10)
        assert pool.effective_max == 30
        pool.apply_heal(10)
        assert pool.current == 30

    def test_percentage(self) -> None:
        pool = StatPool(current=15, max=20)
        assert pool.percentage == 75.0


class TestAttributes:
    def test_default_values(self) -> None:
        attrs = Attributes()
        assert attrs.strength == 10
        assert attrs.charisma == 10

    def test_modifier_calculation(self) -> None:
        attrs = Attributes(strength=16, dexterity=8, constitution=10)
        assert attrs.get_modifier("strength") == 3
        assert attrs.get_modifier("dexterity") == -1
        assert attrs.get_modifier("constitution") == 0

    def test_summary(self) -> None:
        attrs = Attributes(strength=16)
        summary = attrs.to_summary()
        assert "STR: 16 (+3)" in summary


class TestCharacter:
    def test_creation(self) -> None:
        char = Character(name="Aldric")
        assert char.name == "Aldric"
        assert char.level == 1
        assert char.is_alive
        assert char.character_class == CharacterClass.WARRIOR

    def test_is_npc(self) -> None:
        npc = Character(name="Guard")
        assert npc.is_npc

        player = Character(name="Hero", player_id="p1")
        assert not player.is_npc

    def test_level_up(self) -> None:
        char = Character(name="Hero", experience=100)
        assert char.can_level_up()
        success = char.level_up()
        assert success
        assert char.level == 2
        assert char.hp.max == 30
        assert char.hp.current == 30

    def test_cannot_level_up_without_xp(self) -> None:
        char = Character(name="Hero", experience=50)
        assert not char.can_level_up()
        assert not char.level_up()

    def test_add_condition(self) -> None:
        char = Character(name="Hero")
        cond = Condition(name="Poisoned", type=ConditionType.POISON)
        char.add_condition(cond)
        assert len(char.conditions) == 1
        assert char.conditions[0].name == "Poisoned"

    def test_remove_condition(self) -> None:
        char = Character(name="Hero")
        cond = Condition(name="Poisoned", type=ConditionType.POISON)
        char.add_condition(cond)
        assert char.remove_condition("Poisoned")
        assert len(char.conditions) == 0

    def test_tick_conditions(self) -> None:
        char = Character(name="Hero")
        cond = Condition(
            name="Burning",
            type=ConditionType.DEBUFF,
            duration_type=DurationType.ROUNDS,
            remaining=2,
        )
        char.add_condition(cond)
        expired = char.tick_conditions()
        assert len(expired) == 0
        assert char.conditions[0].remaining == 1
        expired = char.tick_conditions()
        assert "Burning" in expired
        assert len(char.conditions) == 0

    def test_context_string(self) -> None:
        char = Character(name="Aldric", level=5)
        ctx = char.to_context_string()
        assert "Aldric" in ctx
        assert "Niveau 5" in ctx


class TestCharacterManager:
    def test_create(self, character_manager: CharacterManager) -> None:
        char = character_manager.create("Hero", CharacterClass.MAGE, "p1")
        assert char.name == "Hero"
        assert char.character_class == CharacterClass.MAGE
        assert char.player_id == "p1"

    def test_get(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        found = character_manager.get(sample_character.id)
        assert found.id == sample_character.id

    def test_get_not_found(self, character_manager: CharacterManager) -> None:
        with pytest.raises(CharacterError):
            character_manager.get("nonexistent")

    def test_list_active(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        active = character_manager.list_active()
        assert len(active) >= 1

    def test_delete(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        character_manager.delete(sample_character.id)
        with pytest.raises(CharacterError):
            character_manager.get(sample_character.id)

    def test_apply_damage(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        actual = character_manager.apply_damage(sample_character.id, 5)
        assert actual == 5
        assert sample_character.hp.current == 15

    def test_apply_damage_negative(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        with pytest.raises(ValidationError):
            character_manager.apply_damage(sample_character.id, -5)

    def test_apply_heal(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        character_manager.apply_damage(sample_character.id, 10)
        actual = character_manager.apply_heal(sample_character.id, 5)
        assert actual == 5
        assert sample_character.hp.current == 15

    def test_add_experience_and_level_up(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        leveled = character_manager.add_experience(sample_character.id, 100)
        assert leveled
        assert sample_character.level == 2

    def test_move(
        self, character_manager: CharacterManager, sample_character: Character
    ) -> None:
        character_manager.move(sample_character.id, "tavern")
        assert sample_character.location == "tavern"

    def test_export_import(self, character_manager: CharacterManager) -> None:
        character_manager.create("A", CharacterClass.MAGE)
        character_manager.create("B", CharacterClass.ROGUE)
        data = character_manager.export_all()
        assert len(data) == 2

        new_manager = CharacterManager()
        count = new_manager.import_characters(data)
        assert count == 2
