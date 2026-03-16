from __future__ import annotations

import contextlib

from pydantic import BaseModel, Field

from src.core.exceptions import (
    InsufficientSpaceError,
    ItemNotFoundError,
    ValidationError,
    WeightLimitExceededError,
)
from src.inventory.item import (
    SLOT_ALLOWED_TYPES,
    EquipmentSlot,
    Item,
)


class InventoryConfig(BaseModel):
    max_slots: int = Field(default=100, ge=1)
    max_weight: float = Field(default=100.0, ge=0.0)


class Inventory(BaseModel):
    items: list[Item] = Field(default_factory=list)
    equipment: dict[EquipmentSlot, str | None] = Field(
        default_factory=lambda: {slot: None for slot in EquipmentSlot}
    )
    config: InventoryConfig = Field(default_factory=InventoryConfig)

    @property
    def total_weight(self) -> float:
        return sum(item.total_weight for item in self.items)

    @property
    def slot_count(self) -> int:
        return len(self.items)

    @property
    def is_full(self) -> bool:
        return self.slot_count >= self.config.max_slots

    def find_item(self, item_id: str) -> Item:
        for item in self.items:
            if item.id == item_id:
                return item
        raise ItemNotFoundError(
            f"Item not found: {item_id}",
            context={"item_id": item_id},
        )

    def find_by_template(self, template_id: str) -> list[Item]:
        return [i for i in self.items if i.template_id == template_id]

    def can_add(self, item: Item) -> bool:
        new_weight = self.total_weight + item.total_weight
        if new_weight > self.config.max_weight:
            return False
        if item.stackable and item.template_id:
            existing = self.find_by_template(item.template_id)
            if existing:
                for e in existing:
                    if e.quantity + item.quantity <= e.max_stack:
                        return True
        return not self.slot_count >= self.config.max_slots

    def add(self, item: Item) -> Item:
        new_weight = self.total_weight + item.total_weight
        if new_weight > self.config.max_weight:
            raise WeightLimitExceededError(
                f"Adding {item.name} ({item.total_weight:.1f}kg) would exceed "
                f"weight limit ({self.total_weight:.1f}/{self.config.max_weight:.1f}kg)",
                context={"item_name": item.name, "item_weight": item.total_weight},
            )

        if item.stackable and item.template_id:
            existing = self.find_by_template(item.template_id)
            for e in existing:
                space = e.max_stack - e.quantity
                if space > 0:
                    to_add = min(space, item.quantity)
                    e.quantity += to_add
                    item.quantity -= to_add
                    if item.quantity <= 0:
                        return e

        if self.slot_count >= self.config.max_slots:
            raise InsufficientSpaceError(
                f"Inventory full ({self.slot_count}/{self.config.max_slots} slots)",
                context={"current_slots": self.slot_count},
            )

        self.items.append(item)
        return item

    def remove(self, item_id: str, quantity: int = 1) -> Item:
        if quantity < 1:
            raise ValidationError(f"Quantity must be positive, got {quantity}")
        item = self.find_item(item_id)

        for slot, equipped_id in self.equipment.items():
            if equipped_id == item_id:
                self.equipment[slot] = None

        if item.quantity > quantity:
            item.quantity -= quantity
            return item.model_copy(update={"quantity": quantity})
        elif item.quantity == quantity:
            self.items.remove(item)
            return item
        else:
            raise ValidationError(
                f"Cannot remove {quantity} of {item.name}, only {item.quantity} available"
            )

    def equip(self, item_id: str, slot: EquipmentSlot) -> Item | None:
        item = self.find_item(item_id)
        allowed = SLOT_ALLOWED_TYPES.get(slot, set())
        if item.type not in allowed:
            raise ValidationError(
                f"Cannot equip {item.type.value} in slot {slot.value}. "
                f"Allowed: {', '.join(t.value for t in allowed)}"
            )

        previous_id = self.equipment.get(slot)
        previous_item: Item | None = None
        if previous_id:
            with contextlib.suppress(ItemNotFoundError):
                previous_item = self.find_item(previous_id)

        self.equipment[slot] = item_id
        return previous_item

    def unequip(self, slot: EquipmentSlot) -> Item | None:
        item_id = self.equipment.get(slot)
        if item_id is None:
            return None
        self.equipment[slot] = None
        try:
            return self.find_item(item_id)
        except ItemNotFoundError:
            return None

    def get_equipped(self, slot: EquipmentSlot) -> Item | None:
        item_id = self.equipment.get(slot)
        if item_id is None:
            return None
        try:
            return self.find_item(item_id)
        except ItemNotFoundError:
            return None

    def to_summary(self) -> str:
        lines = [
            f"Inventaire ({self.slot_count}/{self.config.max_slots} slots, "
            f"{self.total_weight:.1f}/{self.config.max_weight:.1f} kg)"
        ]
        for item in self.items:
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            equipped = ""
            for slot, eid in self.equipment.items():
                if eid == item.id:
                    equipped = f" [E:{slot.value}]"
                    break
            lines.append(f"  - {item.name}{qty} ({item.rarity.value}){equipped}")
        return "\n".join(lines)
