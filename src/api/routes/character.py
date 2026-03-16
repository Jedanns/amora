import logging

from fastapi import APIRouter

from src.api.deps import get_app_state
from src.api.schemas.requests import (
    AddExperienceRequest,
    AddItemRequest,
    CreateCharacterRequest,
    DamageHealRequest,
    MoveCharacterRequest,
)
from src.api.schemas.responses import (
    CharacterListResponse,
    CharacterResponse,
    InventoryResponse,
    ItemResponse,
)
from src.character.models import CharacterClass
from src.inventory.item import Item, ItemType, Rarity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/character", tags=["character"])


def _char_to_response(char: object) -> CharacterResponse:
    from src.character.models import Character

    assert isinstance(char, Character)
    return CharacterResponse(
        id=char.id,
        name=char.name,
        character_class=char.character_class.value,
        level=char.level,
        hp_current=char.hp.current,
        hp_max=char.hp.effective_max,
        mana_current=char.mana.current,
        mana_max=char.mana.effective_max,
        location=char.location,
        is_alive=char.is_alive,
        experience=char.experience,
        attributes={
            "strength": char.attributes.strength,
            "dexterity": char.attributes.dexterity,
            "constitution": char.attributes.constitution,
            "intelligence": char.attributes.intelligence,
            "wisdom": char.attributes.wisdom,
            "charisma": char.attributes.charisma,
        },
        conditions=[c.name for c in char.conditions],
    )


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(request: CreateCharacterRequest) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None

    try:
        char_class = CharacterClass(request.character_class)
    except ValueError:
        char_class = CharacterClass.WARRIOR

    character = app.engine.create_character(
        name=request.name,
        character_class=char_class,
        player_id=request.player_id,
    )
    return _char_to_response(character)


@router.get("", response_model=CharacterListResponse)
async def list_characters() -> CharacterListResponse:
    app = get_app_state()
    assert app.engine is not None
    chars = app.engine.characters.list_active()
    return CharacterListResponse(
        characters=[_char_to_response(c) for c in chars],
        total=len(chars),
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None
    char = app.engine.characters.get(character_id)
    return _char_to_response(char)


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: str) -> None:
    app = get_app_state()
    assert app.engine is not None
    app.engine.characters.delete(character_id)


@router.post("/{character_id}/damage", response_model=CharacterResponse)
async def apply_damage(
    character_id: str, request: DamageHealRequest
) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None
    app.engine.characters.apply_damage(character_id, request.amount)
    char = app.engine.characters.get(character_id)
    return _char_to_response(char)


@router.post("/{character_id}/heal", response_model=CharacterResponse)
async def apply_heal(
    character_id: str, request: DamageHealRequest
) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None
    app.engine.characters.apply_heal(character_id, request.amount)
    char = app.engine.characters.get(character_id)
    return _char_to_response(char)


@router.post("/{character_id}/experience", response_model=CharacterResponse)
async def add_experience(
    character_id: str, request: AddExperienceRequest
) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None
    app.engine.characters.add_experience(character_id, request.amount)
    char = app.engine.characters.get(character_id)
    return _char_to_response(char)


@router.post("/{character_id}/move", response_model=CharacterResponse)
async def move_character(
    character_id: str, request: MoveCharacterRequest
) -> CharacterResponse:
    app = get_app_state()
    assert app.engine is not None
    app.engine.characters.move(character_id, request.location)
    char = app.engine.characters.get(character_id)
    return _char_to_response(char)


@router.get("/{character_id}/inventory", response_model=InventoryResponse)
async def get_inventory(character_id: str) -> InventoryResponse:
    app = get_app_state()
    assert app.engine is not None
    inventory = app.engine.get_inventory(character_id)
    items = [
        ItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            item_type=item.type.value,
            rarity=item.rarity.value,
            quantity=item.quantity,
            weight=item.weight,
            value=item.value,
        )
        for item in inventory.items
    ]
    return InventoryResponse(
        character_id=character_id,
        items=items,
        total_weight=inventory.total_weight,
        max_weight=inventory.config.max_weight,
        used_slots=inventory.slot_count,
        max_slots=inventory.config.max_slots,
    )


@router.post("/{character_id}/inventory", response_model=ItemResponse, status_code=201)
async def add_item(character_id: str, request: AddItemRequest) -> ItemResponse:
    app = get_app_state()
    assert app.engine is not None

    try:
        item_type = ItemType(request.item_type)
    except ValueError:
        item_type = ItemType.MISC

    try:
        rarity = Rarity(request.rarity)
    except ValueError:
        rarity = Rarity.COMMON

    item = Item(
        name=request.name,
        description=request.description,
        type=item_type,
        rarity=rarity,
        quantity=request.quantity,
        weight=request.weight,
        value=request.value,
    )
    added = app.engine.add_item_to_inventory(character_id, item)
    return ItemResponse(
        id=added.id,
        name=added.name,
        description=added.description,
        item_type=added.type.value,
        rarity=added.rarity.value,
        quantity=added.quantity,
        weight=added.weight,
        value=added.value,
    )
