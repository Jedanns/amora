import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import get_app_state
from src.api.schemas.requests import (
    CreateSessionRequest,
    ProcessInputRequest,
    RollDiceRequest,
)
from src.api.schemas.responses import (
    ActionResponse,
    DiceRollResponse,
    GameStateResponse,
    HistoryEntryResponse,
    HistoryResponse,
    NarrativeResponse,
    SessionResponse,
)
from src.core.exceptions import SessionError
from src.llm.gateway import GenerationParams
from src.llm.parser import ResponseParser
from src.memory.context import ContextInput

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
            stream = await app.llm_gateway.generate_stream(
                context_result.prompt, params
            )
            async for chunk in stream:
                full_response += chunk
                await websocket.send_json({"type": "chunk", "text": chunk})

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
