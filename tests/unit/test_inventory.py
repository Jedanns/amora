import pytest

from src.core.exceptions import (
    InsufficientSpaceError,
    ItemNotFoundError,
    ValidationError,
    WeightLimitExceededError,
)
from src.inventory.item import EquipmentSlot, Item, ItemType
from src.inventory.manager import Inventory, InventoryConfig


class TestItem:
    def test_creation(self, sample_sword: Item) -> None:
        assert sample_sword.name == "Iron Sword"
        assert sample_sword.type == ItemType.WEAPON
        assert sample_sword.weight == 3.0

    def test_total_weight(self, sample_potion: Item) -> None:
        sample_potion.quantity = 5
        assert sample_potion.total_weight == 2.5

    def test_can_stack(self, sample_potion: Item) -> None:
        other = Item(
            name="Health Potion",
            template_id="potion_health",
            type=ItemType.CONSUMABLE,
            stackable=True,
            max_stack=10,
        )
        assert sample_potion.can_stack_with(other)

    def test_cannot_stack_different_template(self, sample_potion: Item) -> None:
        other = Item(
            name="Mana Potion",
            template_id="potion_mana",
            type=ItemType.CONSUMABLE,
            stackable=True,
            max_stack=10,
        )
        assert not sample_potion.can_stack_with(other)

    def test_cannot_stack_non_stackable(self, sample_sword: Item) -> None:
        other = Item(name="Another Sword", type=ItemType.WEAPON)
        assert not sample_sword.can_stack_with(other)

    def test_split(self, sample_potion: Item) -> None:
        sample_potion.quantity = 5
        new_item = sample_potion.split(2)
        assert sample_potion.quantity == 3
        assert new_item.quantity == 2
        assert new_item.id != sample_potion.id


class TestInventory:
    def test_add_item(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        assert inventory.slot_count == 1
        assert inventory.total_weight == 3.0

    def test_find_item(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        found = inventory.find_item(sample_sword.id)
        assert found.id == sample_sword.id

    def test_find_item_not_found(self, inventory: Inventory) -> None:
        with pytest.raises(ItemNotFoundError):
            inventory.find_item("nonexistent")

    def test_remove_item(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        removed = inventory.remove(sample_sword.id)
        assert removed.id == sample_sword.id
        assert inventory.slot_count == 0

    def test_remove_partial_stack(
        self, inventory: Inventory, sample_potion: Item
    ) -> None:
        sample_potion.quantity = 5
        inventory.add(sample_potion)
        removed = inventory.remove(sample_potion.id, 2)
        assert removed.quantity == 2
        assert sample_potion.quantity == 3

    def test_remove_too_many(self, inventory: Inventory, sample_potion: Item) -> None:
        sample_potion.quantity = 3
        inventory.add(sample_potion)
        with pytest.raises(ValidationError):
            inventory.remove(sample_potion.id, 5)

    def test_stack_items(self, inventory: Inventory) -> None:
        potion1 = Item(
            name="Health Potion",
            template_id="potion_health",
            type=ItemType.CONSUMABLE,
            stackable=True,
            max_stack=10,
            quantity=3,
            weight=0.5,
        )
        potion2 = Item(
            name="Health Potion",
            template_id="potion_health",
            type=ItemType.CONSUMABLE,
            stackable=True,
            max_stack=10,
            quantity=2,
            weight=0.5,
        )
        inventory.add(potion1)
        inventory.add(potion2)
        assert inventory.slot_count == 1
        assert potion1.quantity == 5

    def test_weight_limit(self, inventory: Inventory) -> None:
        heavy_item = Item(name="Boulder", weight=60.0)
        with pytest.raises(WeightLimitExceededError):
            inventory.add(heavy_item)

    def test_slot_limit(self) -> None:
        inv = Inventory(config=InventoryConfig(max_slots=2, max_weight=1000.0))
        inv.add(Item(name="A"))
        inv.add(Item(name="B"))
        with pytest.raises(InsufficientSpaceError):
            inv.add(Item(name="C"))

    def test_equip_weapon(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        previous = inventory.equip(sample_sword.id, EquipmentSlot.MAIN_HAND)
        assert previous is None
        assert inventory.equipment[EquipmentSlot.MAIN_HAND] == sample_sword.id

    def test_equip_wrong_slot(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        with pytest.raises(ValidationError):
            inventory.equip(sample_sword.id, EquipmentSlot.HEAD)

    def test_unequip(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        inventory.equip(sample_sword.id, EquipmentSlot.MAIN_HAND)
        unequipped = inventory.unequip(EquipmentSlot.MAIN_HAND)
        assert unequipped is not None
        assert unequipped.id == sample_sword.id
        assert inventory.equipment[EquipmentSlot.MAIN_HAND] is None

    def test_unequip_empty_slot(self, inventory: Inventory) -> None:
        result = inventory.unequip(EquipmentSlot.MAIN_HAND)
        assert result is None

    def test_get_equipped(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        inventory.equip(sample_sword.id, EquipmentSlot.MAIN_HAND)
        equipped = inventory.get_equipped(EquipmentSlot.MAIN_HAND)
        assert equipped is not None
        assert equipped.id == sample_sword.id

    def test_summary(self, inventory: Inventory, sample_sword: Item) -> None:
        inventory.add(sample_sword)
        summary = inventory.to_summary()
        assert "Iron Sword" in summary
        assert "1/10 slots" in summary

    def test_can_add(self, inventory: Inventory, sample_sword: Item) -> None:
        assert inventory.can_add(sample_sword)

    def test_can_add_when_full(self) -> None:
        inv = Inventory(config=InventoryConfig(max_slots=1, max_weight=1000.0))
        inv.add(Item(name="A"))
        assert not inv.can_add(Item(name="B"))
