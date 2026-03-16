from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    QUEST_ITEM = "quest_item"
    MATERIAL = "material"
    MISC = "misc"


class Rarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"


class ItemEffect(BaseModel):
    type: str
    target: str = "self"
    value: int = 0
    duration: int | None = None
    description: str = ""


class ItemStats(BaseModel):
    damage: int = 0
    armor: int = 0
    magic_power: int = 0
    speed: int = 0
    bonus_attributes: dict[str, int] = Field(default_factory=dict)


class ItemRequirements(BaseModel):
    level: int = 0
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    character_class: str | None = None


class ItemMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = ""
    lore_text: str = ""


class Item(BaseModel):
    id: str = Field(default_factory=lambda: f"item_{uuid4().hex[:8]}")
    template_id: str = ""
    name: str = Field(min_length=1, max_length=100)
    description: str = ""

    type: ItemType = ItemType.MISC
    rarity: Rarity = Rarity.COMMON

    stackable: bool = False
    max_stack: int = 1
    quantity: int = Field(default=1, ge=1)

    weight: float = Field(default=0.0, ge=0.0)
    value: int = Field(default=0, ge=0)

    stats: ItemStats | None = None
    effects: list[ItemEffect] = Field(default_factory=list)
    requirements: ItemRequirements | None = None

    metadata: ItemMetadata = Field(default_factory=ItemMetadata)

    @property
    def total_weight(self) -> float:
        return self.weight * self.quantity

    def can_stack_with(self, other: Item) -> bool:
        return (
            self.stackable
            and other.stackable
            and self.template_id == other.template_id
            and self.template_id != ""
        )

    def split(self, amount: int) -> Item:
        if amount >= self.quantity or amount < 1:
            raise ValueError(f"Cannot split {amount} from stack of {self.quantity}")
        self.quantity -= amount
        new_item = self.model_copy(
            update={"id": f"item_{uuid4().hex[:8]}", "quantity": amount}
        )
        return new_item


class EquipmentSlot(StrEnum):
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    RING_LEFT = "ring_left"
    RING_RIGHT = "ring_right"
    NECK = "neck"
    BACK = "back"


SLOT_ALLOWED_TYPES: dict[EquipmentSlot, set[ItemType]] = {
    EquipmentSlot.HEAD: {ItemType.ARMOR, ItemType.ACCESSORY},
    EquipmentSlot.CHEST: {ItemType.ARMOR},
    EquipmentSlot.LEGS: {ItemType.ARMOR},
    EquipmentSlot.FEET: {ItemType.ARMOR},
    EquipmentSlot.HANDS: {ItemType.ARMOR, ItemType.ACCESSORY},
    EquipmentSlot.MAIN_HAND: {ItemType.WEAPON},
    EquipmentSlot.OFF_HAND: {ItemType.WEAPON, ItemType.ARMOR},
    EquipmentSlot.RING_LEFT: {ItemType.ACCESSORY},
    EquipmentSlot.RING_RIGHT: {ItemType.ACCESSORY},
    EquipmentSlot.NECK: {ItemType.ACCESSORY},
    EquipmentSlot.BACK: {ItemType.ARMOR, ItemType.ACCESSORY},
}
