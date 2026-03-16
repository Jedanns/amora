from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.lore.entry import LorebookEntry

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class InjectionBudget:
    max_tokens: int = 16384
    reserve_response: int = 512
    system_prompt_tokens: int = 200
    history_tokens: int = 0

    @property
    def available(self) -> int:
        return max(
            0,
            self.max_tokens
            - self.reserve_response
            - self.system_prompt_tokens
            - self.history_tokens,
        )


@dataclass(frozen=True)
class InjectedEntry:
    entry: LorebookEntry
    content: str
    tokens: int
    priority: int
    order: int
    truncated: bool = False


@dataclass
class InjectionResult:
    entries: list[InjectedEntry] = field(default_factory=list)
    total_tokens: int = 0
    budget_used: int = 0
    budget_available: int = 0
    dropped_entries: list[str] = field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def to_text(self) -> str:
        sorted_entries = sorted(
            self.entries, key=lambda e: (e.priority, -e.order), reverse=True
        )
        return "\n\n".join(e.content for e in sorted_entries)


class InjectionPipeline:
    def __init__(
        self,
        budget: InjectionBudget | None = None,
        variables: dict[str, str] | None = None,
    ) -> None:
        self._budget = budget or InjectionBudget()
        self._variables = variables or {}

    @property
    def budget(self) -> InjectionBudget:
        return self._budget

    def set_variables(self, variables: dict[str, str]) -> None:
        self._variables.update(variables)

    def inject(
        self,
        triggered_entries: list[LorebookEntry],
    ) -> InjectionResult:
        available = self._budget.available
        result = InjectionResult(budget_available=available)

        unique_entries = self._deduplicate(triggered_entries)
        sorted_entries = sorted(
            unique_entries,
            key=lambda e: (e.priority, -e.order),
            reverse=True,
        )

        remaining = available
        for entry in sorted_entries:
            content = entry.to_injection_text(self._variables)
            tokens = estimate_tokens(content)

            if tokens <= remaining:
                injected = InjectedEntry(
                    entry=entry,
                    content=content,
                    tokens=tokens,
                    priority=entry.priority,
                    order=entry.order,
                )
                result.entries.append(injected)
                remaining -= tokens
            elif (
                entry.truncatable
                and entry.min_tokens > 0
                and entry.min_tokens <= remaining
            ):
                truncated_content = self._truncate_content(content, remaining)
                truncated_tokens = estimate_tokens(truncated_content)
                injected = InjectedEntry(
                    entry=entry,
                    content=truncated_content,
                    tokens=truncated_tokens,
                    priority=entry.priority,
                    order=entry.order,
                    truncated=True,
                )
                result.entries.append(injected)
                remaining -= truncated_tokens
            else:
                result.dropped_entries.append(entry.id)
                logger.debug(
                    "Dropped entry %s (%d tokens, %d remaining)",
                    entry.id,
                    tokens,
                    remaining,
                )

        result.total_tokens = available - remaining
        result.budget_used = result.total_tokens
        return result

    def _deduplicate(self, entries: list[LorebookEntry]) -> list[LorebookEntry]:
        seen: set[str] = set()
        unique: list[LorebookEntry] = []
        for entry in entries:
            if entry.id not in seen:
                seen.add(entry.id)
                unique.append(entry)
        return unique

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content
        truncated = content[:max_chars]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")
        cut_point = max(last_period, last_newline)
        if cut_point > max_chars // 2:
            truncated = truncated[: cut_point + 1]
        return truncated.rstrip() + "..."
