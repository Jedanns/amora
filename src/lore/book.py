from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.lore.entry import LorebookCategory, LorebookEntry
from src.lore.injection import InjectionBudget, InjectionPipeline, InjectionResult
from src.lore.trigger import TriggerEngine, TriggerResult

logger = logging.getLogger(__name__)


class Lorebook:
    def __init__(
        self,
        fuzzy_threshold: float = 0.85,
    ) -> None:
        self._entries: dict[str, LorebookEntry] = {}
        self._trigger_engine = TriggerEngine(fuzzy_threshold=fuzzy_threshold)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def add_entry(self, entry: LorebookEntry) -> None:
        self._entries[entry.id] = entry
        logger.debug("Added lore entry: %s (%s)", entry.name, entry.id)

    def remove_entry(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def get_entry(self, entry_id: str) -> LorebookEntry | None:
        return self._entries.get(entry_id)

    def get_entries_by_category(
        self, category: LorebookCategory
    ) -> list[LorebookEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def get_constant_entries(self) -> list[LorebookEntry]:
        return self.get_entries_by_category(LorebookCategory.CONSTANT)

    def list_entries(self) -> list[LorebookEntry]:
        return list(self._entries.values())

    def search_by_name(self, query: str) -> list[LorebookEntry]:
        query_lower = query.lower()
        return [e for e in self._entries.values() if query_lower in e.name.lower()]

    def evaluate_triggers(
        self,
        text: str,
        messages: list[str] | None = None,
        game_state: dict[str, object] | None = None,
    ) -> list[TriggerResult]:
        results: list[TriggerResult] = []
        for entry in self._entries.values():
            if not entry.enabled:
                continue
            result = self._trigger_engine.evaluate(entry, text, messages, game_state)
            if result.matched:
                results.append(result)
        return results

    def get_triggered_entries(
        self,
        text: str,
        messages: list[str] | None = None,
        game_state: dict[str, object] | None = None,
    ) -> list[LorebookEntry]:
        trigger_results = self.evaluate_triggers(text, messages, game_state)
        triggered: list[LorebookEntry] = []
        for result in trigger_results:
            entry = self._entries.get(result.entry_id)
            if entry:
                triggered.append(entry)
        return triggered

    def build_injection(
        self,
        text: str,
        messages: list[str] | None = None,
        game_state: dict[str, object] | None = None,
        budget: InjectionBudget | None = None,
        variables: dict[str, str] | None = None,
    ) -> InjectionResult:
        triggered = self.get_triggered_entries(text, messages, game_state)
        pipeline = InjectionPipeline(budget=budget, variables=variables)
        return pipeline.inject(triggered)

    def load_from_directory(self, lore_dir: str | Path) -> int:
        lore_path = Path(lore_dir)
        if not lore_path.exists():
            logger.warning("Lore directory not found: %s", lore_dir)
            return 0

        count = 0
        for json_file in sorted(lore_path.rglob("*.json")):
            try:
                loaded = self._load_file(json_file)
                count += loaded
            except Exception:
                logger.exception("Failed to load lore file: %s", json_file)
        logger.info("Loaded %d lore entries from %s", count, lore_dir)
        return count

    def _load_file(self, path: Path) -> int:
        with open(path, encoding="utf-8") as f:
            data: Any = json.load(f)

        count = 0
        if isinstance(data, list):
            for item in data:
                entry = LorebookEntry.model_validate(item)
                self.add_entry(entry)
                count += 1
        elif isinstance(data, dict):
            if "entries" in data:
                for item in data["entries"]:
                    entry = LorebookEntry.model_validate(item)
                    entry.metadata.source_file = str(path)
                    self.add_entry(entry)
                    count += 1
            else:
                entry = LorebookEntry.model_validate(data)
                entry.metadata.source_file = str(path)
                self.add_entry(entry)
                count += 1

        return count

    @classmethod
    def from_directory(cls, lore_dir: str | Path, **kwargs: Any) -> Lorebook:
        book = cls(**kwargs)
        book.load_from_directory(lore_dir)
        return book

    def export_entries(self) -> list[dict[str, Any]]:
        return [e.model_dump(mode="json") for e in self._entries.values()]

    def import_entries(self, data: list[dict[str, Any]]) -> int:
        count = 0
        for item in data:
            entry = LorebookEntry.model_validate(item)
            self.add_entry(entry)
            count += 1
        return count
