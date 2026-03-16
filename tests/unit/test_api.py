from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import src.api.deps as deps_module
from src.api.deps import AppState
from src.api.main import create_app
from src.core.config import Config
from src.core.engine import GameEngine
from src.llm.gateway import ResilientLLMGateway
from src.llm.mock import MockLLMProvider
from src.lore.book import Lorebook
from src.memory.context import ContextManager
from src.memory.summary import Summarizer
from src.persistence.database import Database


@pytest.fixture
async def app_state() -> AppState:
    cfg = Config()
    db = Database(":memory:")
    engine = GameEngine(config=cfg, database=db)
    await engine.initialize()

    provider = MockLLMProvider(
        responses=[
            "Le dragon rugit. Vous dégainez votre épée. [ACTION:attack|dragon|5]"
        ]
    )
    gateway = ResilientLLMGateway(
        provider=provider,
        retry_config=cfg.llm.retry,
        event_bus=engine.events,
    )

    lorebook = Lorebook()
    context_mgr = ContextManager(
        max_context_tokens=cfg.memory.max_context_tokens,
        max_response_tokens=cfg.llm.max_response_tokens,
    )
    summarizer = Summarizer()

    state = AppState(
        config=cfg,
        engine=engine,
        llm_gateway=gateway,
        llm_provider=provider,
        lorebook=lorebook,
        context_manager=context_mgr,
        summarizer=summarizer,
        event_bus=engine.events,
    )
    return state


@pytest.fixture
async def client(app_state: AppState):
    app = create_app()

    old_state = deps_module._app_state
    deps_module._app_state = app_state

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    deps_module._app_state = old_state

    if app_state.engine:
        await app_state.engine.shutdown()


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestGameRoutes:
    async def test_create_session(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/game/session",
            json={"name": "Test Session", "world_id": "default"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert data["name"] == "Test Session"
        assert data["turn"] == 0
        assert data["location"] == "spawn"

    async def test_get_session(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.get(f"/api/game/session/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id

    async def test_get_session_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/game/session/nonexistent")
        assert resp.status_code == 404

    async def test_save_session(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Save Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(f"/api/game/session/{session_id}/save")
        assert resp.status_code == 204

    async def test_save_inactive_session_fails(self, client: AsyncClient) -> None:
        resp = await client.post("/api/game/session/nonexistent/save")
        assert resp.status_code in (404, 409)

    async def test_process_input(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Input Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(
            f"/api/game/session/{session_id}/input",
            json={"message": "J'attaque le dragon!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "narrative" in data
        assert len(data["narrative"]) > 0

    async def test_process_input_with_params(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Param Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(
            f"/api/game/session/{session_id}/input",
            json={"message": "Hello", "temperature": 0.5, "max_tokens": 256},
        )
        assert resp.status_code == 200

    async def test_roll_dice(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Dice Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(
            f"/api/game/session/{session_id}/roll",
            json={"notation": "2d6+3", "reason": "Attack roll"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["notation"] == "2d6+3"
        assert data["reason"] == "Attack roll"
        assert len(data["individual"]) == 2
        assert data["modifier"] == 3

    async def test_advance_turn(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Turn Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(f"/api/game/session/{session_id}/advance-turn")
        assert resp.status_code == 200
        data = resp.json()
        assert data["turn"] == 1

    async def test_rollback(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Rollback Test"},
        )
        session_id = create.json()["session_id"]

        await client.post(f"/api/game/session/{session_id}/advance-turn")
        await client.post(f"/api/game/session/{session_id}/advance-turn")

        resp = await client.post(
            f"/api/game/session/{session_id}/rollback",
            params={"steps": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["turn"] == 1

    async def test_get_history(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "History Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.get(f"/api/game/session/{session_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] >= 1


class TestCharacterRoutes:
    async def test_create_character(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/character",
            json={"name": "Aldric", "character_class": "warrior"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Aldric"
        assert data["character_class"] == "warrior"
        assert data["level"] == 1
        assert data["is_alive"] is True

    async def test_list_characters(self, client: AsyncClient) -> None:
        await client.post(
            "/api/character",
            json={"name": "Char1"},
        )
        await client.post(
            "/api/character",
            json={"name": "Char2"},
        )

        resp = await client.get("/api/character")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    async def test_get_character(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Findable"},
        )
        char_id = create.json()["id"]

        resp = await client.get(f"/api/character/{char_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Findable"

    async def test_get_character_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/character/nonexistent")
        assert resp.status_code == 404

    async def test_delete_character(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Deletable"},
        )
        char_id = create.json()["id"]

        resp = await client.delete(f"/api/character/{char_id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/character/nonexistent")
        assert resp.status_code == 404

    async def test_apply_damage(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Tank"},
        )
        char_id = create.json()["id"]
        initial_hp = create.json()["hp_current"]

        resp = await client.post(
            f"/api/character/{char_id}/damage",
            json={"amount": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["hp_current"] == initial_hp - 10

    async def test_apply_heal(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Healer"},
        )
        char_id = create.json()["id"]

        await client.post(
            f"/api/character/{char_id}/damage",
            json={"amount": 20},
        )

        resp = await client.post(
            f"/api/character/{char_id}/heal",
            json={"amount": 10},
        )
        assert resp.status_code == 200

    async def test_add_experience(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Leveler"},
        )
        char_id = create.json()["id"]

        resp = await client.post(
            f"/api/character/{char_id}/experience",
            json={"amount": 50},
        )
        assert resp.status_code == 200
        assert resp.json()["experience"] == 50

    async def test_move_character(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Mover"},
        )
        char_id = create.json()["id"]

        resp = await client.post(
            f"/api/character/{char_id}/move",
            json={"location": "tavern"},
        )
        assert resp.status_code == 200
        assert resp.json()["location"] == "tavern"

    async def test_get_inventory(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Inventory Holder"},
        )
        char_id = create.json()["id"]

        resp = await client.get(f"/api/character/{char_id}/inventory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["character_id"] == char_id
        assert data["items"] == []

    async def test_add_item_to_inventory(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Collector"},
        )
        char_id = create.json()["id"]

        resp = await client.post(
            f"/api/character/{char_id}/inventory",
            json={
                "name": "Iron Sword",
                "item_type": "weapon",
                "rarity": "common",
                "weight": 3.0,
                "value": 50,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Iron Sword"
        assert data["item_type"] == "weapon"

        inv_resp = await client.get(f"/api/character/{char_id}/inventory")
        assert len(inv_resp.json()["items"]) == 1


class TestLoreRoutes:
    async def test_list_entries_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/lore")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_add_entry(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/lore",
            json={
                "name": "Excalibur",
                "content": "A legendary sword of great power.",
                "keys": ["excalibur", "legendary sword"],
                "category": "constant",
                "priority": 800,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Excalibur"
        assert data["priority"] == 800

    async def test_list_entries_after_add(self, client: AsyncClient) -> None:
        await client.post(
            "/api/lore",
            json={
                "name": "Dragon Lore",
                "content": "Dragons are ancient creatures.",
                "keys": ["dragon"],
            },
        )

        resp = await client.get("/api/lore")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1

    async def test_get_entry(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/lore",
            json={
                "name": "Tavern",
                "content": "The tavern is warm and inviting.",
                "keys": ["tavern"],
            },
        )
        entry_id = create.json()["id"]

        resp = await client.get(f"/api/lore/{entry_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tavern"

    async def test_get_entry_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/lore/nonexistent")
        assert resp.status_code == 400

    async def test_delete_entry(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/lore",
            json={
                "name": "Deletable Lore",
                "content": "This will be deleted.",
                "keys": ["delete"],
            },
        )
        entry_id = create.json()["id"]

        resp = await client.delete(f"/api/lore/{entry_id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/lore/nonexistent")
        assert resp.status_code == 400

    async def test_search_entries(self, client: AsyncClient) -> None:
        await client.post(
            "/api/lore",
            json={
                "name": "Fire Dragon",
                "content": "A mighty fire dragon.",
                "keys": ["fire dragon"],
            },
        )

        resp = await client.post(
            "/api/lore/search",
            json={"query": "Fire", "n_results": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_get_stats(self, client: AsyncClient) -> None:
        resp = await client.get("/api/lore/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entries" in data
        assert "enabled_count" in data

    async def test_trigger(self, client: AsyncClient) -> None:
        await client.post(
            "/api/lore",
            json={
                "name": "Sword Trigger",
                "content": "A trigger entry for swords.",
                "keys": ["sword"],
                "category": "conditional",
            },
        )

        resp = await client.post(
            "/api/lore/trigger",
            json={"text": "I draw my sword"},
        )
        assert resp.status_code == 200


class TestLLMRoutes:
    async def test_health_check(self, client: AsyncClient) -> None:
        resp = await client.get("/api/llm/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "healthy" in data

    async def test_generate(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/llm/generate",
            json={
                "prompt": "Tell me about dragons",
                "max_tokens": 128,
                "temperature": 0.7,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert len(data["text"]) > 0
        assert "tokens_generated" in data

    async def test_stream_generate(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/llm/stream",
            json={
                "prompt": "Tell me a story",
                "max_tokens": 128,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")


class TestSchemaValidation:
    async def test_create_session_empty_name(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/game/session",
            json={},
        )
        assert resp.status_code == 201

    async def test_process_input_empty_message(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Validation Test"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(
            f"/api/game/session/{session_id}/input",
            json={"message": ""},
        )
        assert resp.status_code == 422

    async def test_invalid_dice_notation(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/game/session",
            json={"name": "Dice Validation"},
        )
        session_id = create.json()["session_id"]

        resp = await client.post(
            f"/api/game/session/{session_id}/roll",
            json={"notation": "xyz"},
        )
        assert resp.status_code == 422

    async def test_create_character_empty_name(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/character",
            json={"name": ""},
        )
        assert resp.status_code == 422

    async def test_damage_negative_amount(self, client: AsyncClient) -> None:
        create = await client.post(
            "/api/character",
            json={"name": "Validator"},
        )
        char_id = create.json()["id"]

        resp = await client.post(
            f"/api/character/{char_id}/damage",
            json={"amount": -5},
        )
        assert resp.status_code == 422

    async def test_add_lore_empty_content(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/lore",
            json={"name": "Empty", "content": ""},
        )
        assert resp.status_code == 422

    async def test_generate_empty_prompt(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/llm/generate",
            json={"prompt": ""},
        )
        assert resp.status_code == 422

    async def test_generate_temperature_out_of_range(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/llm/generate",
            json={"prompt": "Test", "temperature": 5.0},
        )
        assert resp.status_code == 422


class TestErrorHandling:
    async def test_404_for_unknown_route(self, client: AsyncClient) -> None:
        resp = await client.get("/api/nonexistent")
        assert resp.status_code == 404

    async def test_rpg_error_mapped_correctly(self, client: AsyncClient) -> None:
        resp = await client.get("/api/character/nonexistent_id_12345")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "CharacterError" in data["error"]
