import pytest

from src.character.manager import CharacterManager
from src.character.models import Character, CharacterClass
from src.core.dice import DiceRoller
from src.inventory.item import Item, ItemType, Rarity
from src.inventory.manager import Inventory, InventoryConfig
from src.quest.manager import QuestManager
from src.quest.models import Objective, ObjectiveType, Quest, QuestType


@pytest.fixture
def dice_roller() -> DiceRoller:
    return DiceRoller(seed=42)


@pytest.fixture
def character_manager() -> CharacterManager:
    return CharacterManager()


@pytest.fixture
def sample_character(character_manager: CharacterManager) -> Character:
    return character_manager.create(
        "Aldric", CharacterClass.WARRIOR, player_id="player_1"
    )


@pytest.fixture
def sample_npc(character_manager: CharacterManager) -> Character:
    return character_manager.create("Guard", CharacterClass.WARRIOR)


@pytest.fixture
def inventory() -> Inventory:
    config = InventoryConfig(max_slots=10, max_weight=50.0)
    return Inventory(config=config)


@pytest.fixture
def sample_sword() -> Item:
    return Item(
        name="Iron Sword",
        template_id="sword_iron",
        type=ItemType.WEAPON,
        rarity=Rarity.COMMON,
        weight=3.0,
        value=50,
    )


@pytest.fixture
def sample_potion() -> Item:
    return Item(
        name="Health Potion",
        template_id="potion_health",
        type=ItemType.CONSUMABLE,
        rarity=Rarity.COMMON,
        stackable=True,
        max_stack=10,
        quantity=1,
        weight=0.5,
        value=25,
    )


@pytest.fixture
def quest_manager() -> QuestManager:
    return QuestManager()


@pytest.fixture
def sample_quest() -> Quest:
    return Quest(
        name="The Lost Sword",
        description="Find the legendary sword hidden in the dungeon.",
        type=QuestType.MAIN,
        objectives=[
            Objective(
                description="Enter the dungeon",
                type=ObjectiveType.EXPLORE,
                target="dungeon_entrance",
            ),
            Objective(
                description="Defeat the guardian",
                type=ObjectiveType.KILL,
                target="guardian",
            ),
            Objective(
                description="Retrieve the sword",
                type=ObjectiveType.COLLECT,
                target="legendary_sword",
            ),
        ],
    )
