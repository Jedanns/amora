import logging

from fastapi import APIRouter, Body

from src.api.deps import get_app_state
from src.api.schemas.requests import AddLoreEntryRequest, SearchLoreRequest
from src.api.schemas.responses import (
    LoreEntryResponse,
    LoreSearchResultResponse,
    LoreStatsResponse,
)
from src.core.exceptions import LoreError
from src.lore.entry import LorebookCategory, LorebookEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lore", tags=["lore"])


def _entry_to_response(entry: LorebookEntry) -> LoreEntryResponse:
    return LoreEntryResponse(
        id=entry.id,
        name=entry.name,
        content=entry.content,
        keys=entry.keys,
        category=entry.category.value,
        priority=entry.priority,
        enabled=entry.enabled,
    )


@router.get("", response_model=list[LoreEntryResponse])
async def list_entries() -> list[LoreEntryResponse]:
    app = get_app_state()
    if app.lorebook is None:
        return []
    return [_entry_to_response(e) for e in app.lorebook.list_entries()]


@router.post("", response_model=LoreEntryResponse, status_code=201)
async def add_entry(request: AddLoreEntryRequest) -> LoreEntryResponse:
    app = get_app_state()
    if app.lorebook is None:
        raise LoreError("Lorebook not initialized")

    try:
        category = LorebookCategory(request.category)
    except ValueError:
        category = LorebookCategory.CONDITIONAL

    entry = LorebookEntry(
        name=request.name,
        content=request.content,
        keys=request.keys,
        secondary_keys=request.secondary_keys,
        category=category,
        priority=request.priority,
        enabled=request.enabled,
    )
    app.lorebook.add_entry(entry)
    return _entry_to_response(entry)


@router.get("/stats", response_model=LoreStatsResponse)
async def get_stats() -> LoreStatsResponse:
    app = get_app_state()
    if app.lorebook is None:
        return LoreStatsResponse(
            total_entries=0,
            categories={},
            enabled_count=0,
            disabled_count=0,
        )

    entries = app.lorebook.list_entries()
    categories: dict[str, int] = {}
    enabled = 0
    disabled = 0
    for entry in entries:
        cat = entry.category.value
        categories[cat] = categories.get(cat, 0) + 1
        if entry.enabled:
            enabled += 1
        else:
            disabled += 1

    return LoreStatsResponse(
        total_entries=len(entries),
        categories=categories,
        enabled_count=enabled,
        disabled_count=disabled,
    )


@router.get("/{entry_id}", response_model=LoreEntryResponse)
async def get_entry(entry_id: str) -> LoreEntryResponse:
    app = get_app_state()
    if app.lorebook is None:
        raise LoreError("Lorebook not initialized")

    entry = app.lorebook.get_entry(entry_id)
    if entry is None:
        raise LoreError(f"Lore entry not found: {entry_id}")
    return _entry_to_response(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str) -> None:
    app = get_app_state()
    if app.lorebook is None:
        raise LoreError("Lorebook not initialized")

    success = app.lorebook.remove_entry(entry_id)
    if not success:
        raise LoreError(f"Lore entry not found: {entry_id}")


@router.post("/search", response_model=LoreSearchResultResponse)
async def search_entries(request: SearchLoreRequest) -> LoreSearchResultResponse:
    app = get_app_state()
    if app.lorebook is None:
        return LoreSearchResultResponse(entries=[], query=request.query, total=0)

    results = app.lorebook.search_by_name(request.query)
    limited = results[: request.n_results]
    return LoreSearchResultResponse(
        entries=[_entry_to_response(e) for e in limited],
        query=request.query,
        total=len(results),
    )


@router.post("/trigger", response_model=list[LoreEntryResponse])
async def get_triggered(text: str = Body(..., embed=True)) -> list[LoreEntryResponse]:
    app = get_app_state()
    if app.lorebook is None:
        return []

    triggered = app.lorebook.get_triggered_entries(text)
    return [_entry_to_response(e) for e in triggered]
