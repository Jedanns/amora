from __future__ import annotations

from datetime import UTC, datetime

from src.character.models import Character, CharacterClass
from src.core.exceptions import CharacterError, ValidationError


class CharacterManager:
    def __init__(self) -> None:
        self._characters: dict[str, Character] = {}

    def create(
        self,
        name: str,
        character_class: CharacterClass = CharacterClass.WARRIOR,
        player_id: str | None = None,
    ) -> Character:
        character = Character(
            name=name,
            character_class=character_class,
            player_id=player_id,
        )
        self._characters[character.id] = character
        return character

    def get(self, character_id: str) -> Character:
        character = self._characters.get(character_id)
        if character is None:
            raise CharacterError(
                f"Character not found: {character_id}",
                context={"character_id": character_id},
            )
        if character.metadata.is_deleted:
            raise CharacterError(
                f"Character has been deleted: {character_id}",
                context={"character_id": character_id},
            )
        return character

    def list_active(self) -> list[Character]:
        return [c for c in self._characters.values() if not c.metadata.is_deleted]

    def list_npcs(self) -> list[Character]:
        return [c for c in self.list_active() if c.is_npc]

    def list_players(self) -> list[Character]:
        return [c for c in self.list_active() if not c.is_npc]

    def delete(self, character_id: str) -> None:
        character = self.get(character_id)
        character.metadata.is_deleted = True
        character.metadata.updated_at = datetime.now(UTC)

    def apply_damage(self, character_id: str, amount: int) -> int:
        if amount < 0:
            raise ValidationError(f"Damage cannot be negative: {amount}")
        character = self.get(character_id)
        actual = character.hp.apply_damage(amount)
        character.metadata.updated_at = datetime.now(UTC)
        return actual

    def apply_heal(self, character_id: str, amount: int) -> int:
        if amount < 0:
            raise ValidationError(f"Heal cannot be negative: {amount}")
        character = self.get(character_id)
        actual = character.hp.apply_heal(amount)
        character.metadata.updated_at = datetime.now(UTC)
        return actual

    def add_experience(self, character_id: str, amount: int) -> bool:
        if amount < 0:
            raise ValidationError(f"Experience cannot be negative: {amount}")
        character = self.get(character_id)
        character.experience += amount
        character.metadata.updated_at = datetime.now(UTC)
        leveled_up = False
        while character.can_level_up():
            character.level_up()
            leveled_up = True
        return leveled_up

    def move(self, character_id: str, location: str) -> None:
        character = self.get(character_id)
        character.location = location
        character.metadata.updated_at = datetime.now(UTC)

    def export_all(self) -> list[dict[str, object]]:
        return [c.model_dump(mode="json") for c in self._characters.values()]

    def import_characters(self, data: list[dict[str, object]]) -> int:
        count = 0
        for char_data in data:
            character = Character.model_validate(char_data)
            self._characters[character.id] = character
            count += 1
        return count
