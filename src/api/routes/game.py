import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import get_app_state
from src.api.schemas.requests import (
    CreateSessionRequest,
    ProcessInputRequest,
    QuestUpdateRequest,
    RollDiceRequest,
)
from src.api.schemas.responses import (
    ActionResponse,
    DiceRollResponse,
    GameStateResponse,
    HistoryEntryResponse,
    HistoryResponse,
    NarrativeResponse,
    ObjectiveResponse,
    QuestListResponse,
    QuestResponse,
    SessionResponse,
)
from src.core.exceptions import SessionError
from src.llm.gateway import GenerationParams
from src.llm.parser import ResponseParser
from src.memory.context import ContextInput
from src.quest.models import Quest, Objective, QuestStatus, QuestType, ObjectiveType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["game"])

SYSTEM_PROMPT = (
    "Tu es le Maître du Jeu (MJ) d'un RPG textuel immersif en français. "
    "Tu narres le monde, les PNJ, les événements et les conséquences des actions du joueur.\n\n"
    "FORMAT DE RÉPONSE :\n"
    "- Écris UNIQUEMENT de la prose narrative fluide, en français.\n"
    "- Les dialogues des PNJ sont entre guillemets.\n"
    "- Termine ta narration à un moment naturel, quand la balle est dans le camp du joueur.\n\n"
    "INTERDIT ABSOLU :\n"
    "- Ne joue JAMAIS le rôle du joueur. Ne parle JAMAIS à sa place. "
    "Ne génère JAMAIS ses actions, ses pensées ou ses paroles.\n"
    "- N'écris JAMAIS de headers markdown (###, ##, #).\n"
    "- N'écris JAMAIS de balises XML ou HTML.\n"
    "- N'écris JAMAIS de remarques méta, de notes au joueur, "
    "ou de parenthèses explicatives hors du récit.\n"
    "- Ne demande JAMAIS 'Qu'est-ce que tu fais ?' ou 'Que fais-tu ?' "
    "ou toute question similaire. Le joueur sait qu'il doit agir.\n"
    "- N'écris JAMAIS de suggestions d'actions entre parenthèses.\n"
    "- N'invente JAMAIS les statistiques du joueur (or, objets, etc.). "
    "Utilise UNIQUEMENT les informations fournies dans le contexte.\n\n"
    "STYLE :\n"
    "- Descriptions sensorielles riches (vue, son, odeur, toucher).\n"
    "- PNJ avec personnalités distinctes et dialogues naturels.\n"
    "- Narration à la deuxième personne (tu).\n"
    "- Longueur adaptée : courte pour une interaction simple, "
    "longue pour une scène importante.\n"
)

LLM_STOP_SEQUENCES = [
    "<|im_end|>",
    "<|im_start|>",
    "<|endoftext|>",
    "[INST]",
    "\nUser:",
    "\nJoueur:",
    "\n(Remarque",
    "\n(Note",
]


def _state_to_response(state: Any) -> GameStateResponse:
    return GameStateResponse(
        session_id=state.session_id,
        turn=state.turn,
        location=state.location,
        combat_active=state.combat_active,
        active_character_id=state.active_character_id,
        flags=state.flags,
        version=state.version,
    )


@router.post("/session", response_model=SessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest) -> SessionResponse:
    app = get_app_state()
    assert app.engine is not None
    state = await app.engine.create_session(
        name=request.name, world_id=request.world_id
    )
    return SessionResponse(
        session_id=state.session_id,
        name=request.name,
        turn=state.turn,
        location=state.location,
        combat_active=state.combat_active,
        active_character_id=state.active_character_id,
        version=state.version,
    )


@router.get("/session/{session_id}", response_model=GameStateResponse)
async def get_session(session_id: str) -> GameStateResponse:
    app = get_app_state()
    assert app.engine is not None
    if app.engine._state is None or app.engine._state.session_id != session_id:
        loaded = await app.engine.load_session(session_id)
        return _state_to_response(loaded)
    return _state_to_response(app.engine.state)


@router.post("/session/{session_id}/save", status_code=204)
async def save_session(session_id: str) -> None:
    app = get_app_state()
    assert app.engine is not None
    if app.engine._state is None or app.engine._state.session_id != session_id:
        raise SessionError(f"Session {session_id} is not active")
    await app.engine.save_session()


@router.get("/session/{session_id}/state", response_model=GameStateResponse)
async def get_game_state(session_id: str) -> GameStateResponse:
    return await get_session(session_id)


@router.post("/session/{session_id}/input", response_model=NarrativeResponse)
async def process_input(
    session_id: str, request: ProcessInputRequest
) -> NarrativeResponse:
    app = get_app_state()
    assert app.engine is not None
    assert app.llm_gateway is not None
    assert app.context_manager is not None

    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)

    engine._add_history("user", request.message)

    all_relevant = [
        h for h in engine.history
        if h.type in ("user", "assistant")
    ]
    conversation_history = [
        {"role": h.type, "content": h.content}
        for h in all_relevant[-21:-1]
    ]

    lore_entries = []
    if app.lorebook:
        lore_entries = app.lorebook.get_triggered_entries(request.message)

    character = None
    if engine.state.active_character_id:
        character = engine.characters.get(engine.state.active_character_id)

    ctx_input = ContextInput(
        user_input=request.message,
        system_prompt=SYSTEM_PROMPT,
        character=character,
        lore_entries=lore_entries,
        conversation_history=conversation_history,
    )
    context_result = app.context_manager.build(ctx_input)

    params = GenerationParams.from_config(app.config.llm)
    params = GenerationParams(
        max_tokens=request.max_tokens or params.max_tokens,
        temperature=request.temperature
        if request.temperature is not None
        else params.temperature,
        top_p=params.top_p,
        top_k=params.top_k,
        stop_sequences=LLM_STOP_SEQUENCES,
    )

    result = await app.llm_gateway.generate(context_result.prompt, params)

    parser = ResponseParser()
    parsed = parser.parse(result.text)

    actions = [
        ActionResponse(type=a.type, target=a.target, value=str(a.value))
        for a in parsed.actions
    ]

    engine._add_history("assistant", parsed.narrative)

    state_response = _state_to_response(engine.state)

    return NarrativeResponse(
        narrative=parsed.narrative,
        actions=actions,
        state=state_response,
    )


@router.post("/session/{session_id}/roll", response_model=DiceRollResponse)
async def roll_dice(session_id: str, request: RollDiceRequest) -> DiceRollResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)

    result = engine.roll_dice(request.notation, request.reason, request.actor_id)
    individual = []
    for comp in result.components:
        individual.extend(comp.rolls)
    return DiceRollResponse(
        id=result.id,
        notation=result.notation,
        individual=list(individual),
        modifier=result.modifier,
        total=result.total,
        reason=request.reason,
    )


@router.post("/session/{session_id}/advance-turn", response_model=GameStateResponse)
async def advance_turn(session_id: str) -> GameStateResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    engine.advance_turn()
    return _state_to_response(engine.state)


@router.post("/session/{session_id}/rollback", response_model=GameStateResponse)
async def rollback(session_id: str, steps: int = 1) -> GameStateResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        raise SessionError(f"Session {session_id} is not active")
    state = engine.rollback(steps)
    return _state_to_response(state)


@router.get("/session/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str, limit: int = 50) -> HistoryResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    entries = engine.history[-limit:]
    return HistoryResponse(
        entries=[
            HistoryEntryResponse(
                id=h.id,
                timestamp=h.timestamp.isoformat(),
                type=h.type,
                content=h.content,
                metadata=h.metadata,
            )
            for h in entries
        ],
        total=len(engine.history),
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    app = get_app_state()
    assert app.engine is not None
    rows = await app.engine._db.list_sessions()
    results: list[SessionResponse] = []
    for row in rows:
        data = await app.engine._db.load_session(row["id"])
        state_data = data.get("state", {}) if data else {}
        char_list = data.get("characters", []) if data else []
        char_name = char_list[0].get("name") if char_list else None
        char_class = char_list[0].get("character_class") if char_list else None
        results.append(
            SessionResponse(
                session_id=row["id"],
                name=row.get("name", row["id"]),
                turn=state_data.get("turn", 0),
                location=state_data.get("location", "spawn"),
                combat_active=state_data.get("combat_active", False),
                active_character_id=state_data.get("active_character_id"),
                version=state_data.get("version", 0),
                character_name=char_name,
                character_class=char_class,
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    return results


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    app = get_app_state()
    assert app.engine is not None
    deleted = await app.engine._db.delete_session(session_id)
    if not deleted:
        raise SessionError(f"Session not found: {session_id}")


@router.post("/session/{session_id}/set-character")
async def set_active_character(session_id: str, character_id: str) -> GameStateResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    engine.state.active_character_id = character_id
    return _state_to_response(engine.state)


def _quest_to_response(quest: Quest) -> QuestResponse:
    return QuestResponse(
        id=quest.id,
        name=quest.name,
        description=quest.description,
        status=quest.status.value,
        objectives=[
            ObjectiveResponse(
                id=o.id,
                description=o.description,
                current=o.current,
                target=o.required,
                completed=o.is_complete,
            )
            for o in quest.objectives
        ],
        progress=quest.progress_pct,
    )


@router.get(
    "/session/{session_id}/quests", response_model=QuestListResponse
)
async def list_quests(session_id: str, status: str | None = None) -> QuestListResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)

    if status == "active":
        quests = engine.quests.list_active()
    elif status == "available":
        quests = engine.quests.list_available()
    elif status == "completed":
        quests = engine.quests.list_completed()
    else:
        quests = list(engine.quests._quests.values())

    return QuestListResponse(
        quests=[_quest_to_response(q) for q in quests],
        total=len(quests),
    )


@router.post(
    "/session/{session_id}/quests",
    response_model=QuestResponse,
    status_code=201,
)
async def add_quest(session_id: str, quest_data: dict[str, Any]) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)

    quest = Quest.model_validate(quest_data)
    engine.quests.add(quest)
    return _quest_to_response(quest)


@router.post(
    "/session/{session_id}/quests/{quest_id}/start",
    response_model=QuestResponse,
)
async def start_quest(session_id: str, quest_id: str) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    quest = engine.quests.start(quest_id)
    return _quest_to_response(quest)


@router.post(
    "/session/{session_id}/quests/{quest_id}/advance",
    response_model=QuestResponse,
)
async def advance_quest_objective(
    session_id: str, quest_id: str, request: QuestUpdateRequest
) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    engine.quests.advance_objective(quest_id, request.objective_id, request.amount)
    quest = engine.quests.get(quest_id)
    return _quest_to_response(quest)


@router.post(
    "/session/{session_id}/quests/{quest_id}/complete",
    response_model=QuestResponse,
)
async def complete_quest(session_id: str, quest_id: str) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    quest = engine.quests.complete(quest_id)
    return _quest_to_response(quest)


@router.post(
    "/session/{session_id}/quests/{quest_id}/fail",
    response_model=QuestResponse,
)
async def fail_quest(session_id: str, quest_id: str) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    quest = engine.quests.fail(quest_id)
    return _quest_to_response(quest)


@router.post(
    "/session/{session_id}/quests/{quest_id}/abandon",
    response_model=QuestResponse,
)
async def abandon_quest(session_id: str, quest_id: str) -> QuestResponse:
    app = get_app_state()
    assert app.engine is not None
    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        await engine.load_session(session_id)
    quest = engine.quests.abandon(quest_id)
    return _quest_to_response(quest)


@router.websocket("/session/{session_id}/stream")
async def stream_game(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    app = get_app_state()
    assert app.engine is not None
    assert app.llm_gateway is not None
    assert app.context_manager is not None

    engine = app.engine
    if engine._state is None or engine._state.session_id != session_id:
        try:
            await engine.load_session(session_id)
        except SessionError:
            await websocket.close(code=4004, reason="Session not found")
            return

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            if not message:
                await websocket.send_json({"error": "Empty message"})
                continue

            engine._add_history("user", message)

            all_relevant = [
                h for h in engine.history
                if h.type in ("user", "assistant")
            ]
            conversation_history = [
                {"role": h.type, "content": h.content}
                for h in all_relevant[-21:-1]
            ]

            lore_entries = []
            if app.lorebook:
                lore_entries = app.lorebook.get_triggered_entries(message)

            character = None
            if engine.state.active_character_id:
                character = engine.characters.get(engine.state.active_character_id)

            ctx_input = ContextInput(
                user_input=message,
                system_prompt=SYSTEM_PROMPT,
                character=character,
                lore_entries=lore_entries,
                conversation_history=conversation_history,
            )
            context_result = app.context_manager.build(ctx_input)

            params = GenerationParams.from_config(app.config.llm)
            params = GenerationParams(
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                top_p=params.top_p,
                top_k=params.top_k,
                stop_sequences=LLM_STOP_SEQUENCES,
            )

            full_response = ""
            in_think_block = False
            pending_buffer = ""
            stream = await app.llm_gateway.generate_stream(
                context_result.prompt, params
            )
            async for chunk in stream:
                full_response += chunk
                pending_buffer += chunk

                while pending_buffer:
                    if in_think_block:
                        end_idx = pending_buffer.find("</think>")
                        if end_idx != -1:
                            pending_buffer = pending_buffer[end_idx + 8:]
                            in_think_block = False
                        else:
                            pending_buffer = ""
                            break
                    else:
                        start_idx = pending_buffer.find("<think>")
                        if start_idx != -1:
                            to_send = pending_buffer[:start_idx]
                            if to_send:
                                await websocket.send_json({"type": "chunk", "text": to_send})
                            pending_buffer = pending_buffer[start_idx + 7:]
                            in_think_block = True
                        elif "<" in pending_buffer and not pending_buffer.endswith(">"):
                            last_lt = pending_buffer.rfind("<")
                            maybe_tag = pending_buffer[last_lt:]
                            if "<think>".startswith(maybe_tag):
                                to_send = pending_buffer[:last_lt]
                                if to_send:
                                    await websocket.send_json({"type": "chunk", "text": to_send})
                                pending_buffer = maybe_tag
                                break
                            else:
                                await websocket.send_json({"type": "chunk", "text": pending_buffer})
                                pending_buffer = ""
                        else:
                            await websocket.send_json({"type": "chunk", "text": pending_buffer})
                            pending_buffer = ""

            if pending_buffer and not in_think_block:
                await websocket.send_json({"type": "chunk", "text": pending_buffer})

            parser = ResponseParser()
            parsed = parser.parse(full_response)

            engine._add_history("assistant", parsed.narrative)

            actions_data = [
                {"type": a.type, "target": a.target, "value": a.value}
                for a in parsed.actions
            ]

            await websocket.send_json(
                {
                    "type": "complete",
                    "narrative": parsed.narrative,
                    "actions": actions_data,
                    "state": _state_to_response(engine.state).model_dump(),
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
        await websocket.close(code=1011, reason="Internal error")
