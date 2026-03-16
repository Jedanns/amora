import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.deps import get_app_state
from src.api.schemas.requests import GenerateRequest
from src.api.schemas.responses import GenerationResponse, LLMHealthResponse
from src.core.exceptions import LLMError
from src.llm.gateway import GenerationParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health", response_model=LLMHealthResponse)
async def health_check() -> LLMHealthResponse:
    app = get_app_state()
    if app.llm_provider is None:
        return LLMHealthResponse(
            healthy=False,
            message="No LLM provider configured",
        )

    try:
        healthy = await app.llm_provider.is_healthy()
        model_info = await app.llm_provider.get_model_info()
        return LLMHealthResponse(
            healthy=healthy,
            provider=app.config.llm.provider,
            model=model_info.get("model", app.config.llm.model),
            message="OK" if healthy else "Provider unhealthy",
        )
    except Exception as exc:
        return LLMHealthResponse(
            healthy=False,
            provider=app.config.llm.provider,
            message=str(exc),
        )


@router.post("/generate", response_model=GenerationResponse)
async def generate(request: GenerateRequest) -> GenerationResponse:
    app = get_app_state()
    if app.llm_gateway is None:
        raise LLMError("LLM gateway not initialized")

    params = GenerationParams(
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        stop_sequences=request.stop_sequences,
    )

    result = await app.llm_gateway.generate(request.prompt, params)

    return GenerationResponse(
        text=result.text,
        tokens_generated=result.tokens_generated,
        generation_time_ms=result.duration_seconds * 1000.0,
        tokens_per_second=result.tokens_per_second,
    )


@router.post("/stream")
async def stream_generate(request: GenerateRequest) -> StreamingResponse:
    app = get_app_state()
    if app.llm_gateway is None:
        raise LLMError("LLM gateway not initialized")

    params = GenerationParams(
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        stop_sequences=request.stop_sequences,
    )

    async def event_generator():
        stream = await app.llm_gateway.generate_stream(request.prompt, params)
        async for chunk in stream:
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
