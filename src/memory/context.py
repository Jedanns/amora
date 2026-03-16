from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.llm.tokens import TokenCounter

if TYPE_CHECKING:
    from src.character.models import Character
    from src.lore.entry import LorebookEntry

logger = logging.getLogger(__name__)

SYSTEM_BUDGET_DEFAULT = 500
RESPONSE_RESERVE_DEFAULT = 512
HISTORY_BUDGET_RATIO = 0.4
LORE_BUDGET_RATIO = 0.3
SUMMARY_BUDGET_RATIO = 0.15
CHARACTER_BUDGET_RATIO = 0.15


@dataclass(frozen=True)
class ContextBudget:
    total: int
    system: int
    response_reserve: int
    character: int
    lore: int
    history: int
    summary: int

    @property
    def available(self) -> int:
        return self.total - self.response_reserve - self.system

    @classmethod
    def calculate(
        cls,
        max_context_tokens: int,
        system_tokens: int = SYSTEM_BUDGET_DEFAULT,
        response_reserve: int = RESPONSE_RESERVE_DEFAULT,
    ) -> ContextBudget:
        available = max_context_tokens - response_reserve - system_tokens
        available = max(0, available)
        return cls(
            total=max_context_tokens,
            system=system_tokens,
            response_reserve=response_reserve,
            character=int(available * CHARACTER_BUDGET_RATIO),
            lore=int(available * LORE_BUDGET_RATIO),
            history=int(available * HISTORY_BUDGET_RATIO),
            summary=int(available * SUMMARY_BUDGET_RATIO),
        )


@dataclass
class ContextSection:
    name: str
    content: str
    tokens: int
    truncated: bool = False


@dataclass
class ContextResult:
    prompt: str
    sections: list[ContextSection]
    total_tokens: int
    budget: ContextBudget
    lore_entries_included: int = 0
    history_messages_included: int = 0
    summary_included: bool = False
    truncated: bool = False

    @property
    def budget_used(self) -> int:
        return self.total_tokens

    @property
    def budget_remaining(self) -> int:
        return self.budget.total - self.budget.response_reserve - self.total_tokens


@dataclass
class ContextInput:
    user_input: str
    system_prompt: str = ""
    character: Character | None = None
    lore_entries: list[LorebookEntry] = field(default_factory=list)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    summary_text: str = ""
    key_facts: list[str] = field(default_factory=list)
    extra_context: str = ""


class ContextOptimizer:
    def __init__(self, token_counter: TokenCounter | None = None) -> None:
        self._counter = token_counter or TokenCounter()
        self._token_cache: dict[int, int] = {}

    def count_tokens(self, text: str) -> int:
        text_hash = hash(text)
        if text_hash not in self._token_cache:
            self._token_cache[text_hash] = self._counter.count(text)
        return self._token_cache[text_hash]

    def select_lore_entries(
        self,
        entries: list[LorebookEntry],
        budget: int,
    ) -> tuple[list[LorebookEntry], int]:
        sorted_entries = sorted(entries, key=lambda e: e.priority, reverse=True)

        constant = [e for e in sorted_entries if e.is_constant]
        non_constant = [e for e in sorted_entries if not e.is_constant]

        selected: list[LorebookEntry] = []
        used_tokens = 0

        for entry in constant:
            tokens = self.count_tokens(entry.to_injection_text())
            if used_tokens + tokens <= budget:
                selected.append(entry)
                used_tokens += tokens

        remaining_budget = budget - used_tokens
        for entry in non_constant:
            text = entry.to_injection_text()
            tokens = self.count_tokens(text)
            if used_tokens + tokens <= budget:
                selected.append(entry)
                used_tokens += tokens
            elif entry.truncatable and remaining_budget > entry.min_tokens > 0:
                truncated = self._counter.truncate_to_budget(text, remaining_budget)
                if truncated:
                    selected.append(entry)
                    used_tokens += self.count_tokens(truncated)
                    break

        return selected, used_tokens

    def select_history(
        self,
        messages: list[dict[str, str]],
        budget: int,
    ) -> tuple[list[dict[str, str]], int]:
        reversed_msgs = list(reversed(messages))
        selected: list[dict[str, str]] = []
        used_tokens = 0

        for msg in reversed_msgs:
            content = msg.get("content", "")
            role = msg.get("role", "")
            line = f"[{role}]: {content}"
            tokens = self.count_tokens(line) + 4
            if used_tokens + tokens <= budget:
                selected.append(msg)
                used_tokens += tokens
            else:
                break

        selected.reverse()
        return selected, used_tokens

    def clear_cache(self) -> None:
        self._token_cache.clear()


class ContextManager:
    def __init__(
        self,
        max_context_tokens: int = 12288,
        max_response_tokens: int = 512,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._max_context = max_context_tokens
        self._max_response = max_response_tokens
        self._counter = token_counter or TokenCounter()
        self._optimizer = ContextOptimizer(self._counter)

    @property
    def max_context_tokens(self) -> int:
        return self._max_context

    @property
    def max_response_tokens(self) -> int:
        return self._max_response

    def build(self, context_input: ContextInput) -> ContextResult:
        system_tokens = self._counter.count(context_input.system_prompt) if context_input.system_prompt else 0
        budget = ContextBudget.calculate(
            max_context_tokens=self._max_context,
            system_tokens=system_tokens,
            response_reserve=self._max_response,
        )

        sections: list[ContextSection] = []
        used_tokens = 0
        truncated = False

        if context_input.system_prompt:
            sections.append(ContextSection(
                name="system",
                content=context_input.system_prompt,
                tokens=system_tokens,
            ))
            used_tokens += system_tokens

        user_tokens = self._counter.count(context_input.user_input)
        remaining = budget.available - user_tokens

        char_text = ""
        char_tokens = 0
        if context_input.character:
            char_text = context_input.character.to_context_string()
            if context_input.extra_context:
                char_text += f"\n\n{context_input.extra_context}"
            char_tokens = self._counter.count(char_text)
            char_budget = min(budget.character, remaining)
            if char_tokens <= char_budget:
                sections.append(ContextSection(
                    name="character",
                    content=char_text,
                    tokens=char_tokens,
                ))
                used_tokens += char_tokens
                remaining -= char_tokens
            else:
                truncated_char = self._counter.truncate_to_budget(char_text, char_budget)
                trunc_tokens = self._counter.count(truncated_char)
                sections.append(ContextSection(
                    name="character",
                    content=truncated_char,
                    tokens=trunc_tokens,
                    truncated=True,
                ))
                used_tokens += trunc_tokens
                remaining -= trunc_tokens
                truncated = True
        elif context_input.extra_context:
            extra_tokens = self._counter.count(context_input.extra_context)
            if extra_tokens <= remaining:
                sections.append(ContextSection(
                    name="character",
                    content=context_input.extra_context,
                    tokens=extra_tokens,
                ))
                used_tokens += extra_tokens
                remaining -= extra_tokens

        summary_text = ""
        summary_tokens = 0
        if context_input.summary_text or context_input.key_facts:
            parts: list[str] = []
            if context_input.summary_text:
                parts.append(context_input.summary_text)
            if context_input.key_facts:
                facts_text = "Faits importants:\n" + "\n".join(
                    f"- {fact}" for fact in context_input.key_facts
                )
                parts.append(facts_text)
            summary_text = "\n\n".join(parts)
            summary_tokens = self._counter.count(summary_text)
            summary_budget = min(budget.summary, remaining)
            if summary_tokens <= summary_budget:
                sections.append(ContextSection(
                    name="summary",
                    content=summary_text,
                    tokens=summary_tokens,
                ))
                used_tokens += summary_tokens
                remaining -= summary_tokens
            elif summary_budget > 10:
                truncated_summary = self._counter.truncate_to_budget(summary_text, summary_budget)
                trunc_tokens = self._counter.count(truncated_summary)
                sections.append(ContextSection(
                    name="summary",
                    content=truncated_summary,
                    tokens=trunc_tokens,
                    truncated=True,
                ))
                used_tokens += trunc_tokens
                remaining -= trunc_tokens
                truncated = True

        lore_count = 0
        if context_input.lore_entries:
            lore_budget = min(budget.lore, remaining)
            selected_lore, lore_tokens = self._optimizer.select_lore_entries(
                context_input.lore_entries, lore_budget
            )
            if selected_lore:
                lore_text = "\n\n".join(
                    entry.to_injection_text() for entry in selected_lore
                )
                sections.append(ContextSection(
                    name="lore",
                    content=lore_text,
                    tokens=lore_tokens,
                ))
                used_tokens += lore_tokens
                remaining -= lore_tokens
                lore_count = len(selected_lore)
                if lore_count < len(context_input.lore_entries):
                    truncated = True

        history_count = 0
        if context_input.conversation_history:
            history_budget = min(budget.history, remaining)
            selected_history, hist_tokens = self._optimizer.select_history(
                context_input.conversation_history, history_budget
            )
            if selected_history:
                history_lines = []
                for msg in selected_history:
                    role = msg.get("role", "system")
                    content = msg.get("content", "")
                    name = msg.get("name", "")
                    prefix = name or role
                    history_lines.append(f"[{prefix}]: {content}")
                history_text = "\n".join(history_lines)
                sections.append(ContextSection(
                    name="history",
                    content=history_text,
                    tokens=hist_tokens,
                ))
                used_tokens += hist_tokens
                remaining -= hist_tokens
                history_count = len(selected_history)
                if history_count < len(context_input.conversation_history):
                    truncated = True

        sections.append(ContextSection(
            name="user",
            content=context_input.user_input,
            tokens=user_tokens,
        ))
        used_tokens += user_tokens

        prompt = self._assemble_prompt(sections)
        total_tokens = self._counter.count(prompt)

        return ContextResult(
            prompt=prompt,
            sections=sections,
            total_tokens=total_tokens,
            budget=budget,
            lore_entries_included=lore_count,
            history_messages_included=history_count,
            summary_included=bool(summary_text),
            truncated=truncated,
        )

    def _assemble_prompt(self, sections: list[ContextSection]) -> str:
        label_map = {
            "system": "INSTRUCTIONS",
            "character": "PERSONNAGE",
            "summary": "RÉSUMÉ",
            "lore": "CONTEXTE DU MONDE",
            "history": "HISTORIQUE",
            "user": "JOUEUR",
        }

        system_parts: list[str] = []
        history_content = ""
        user_content = ""

        for section in sections:
            if section.name == "history":
                history_content = section.content
            elif section.name == "user":
                user_content = section.content
            else:
                label = label_map.get(section.name, section.name.upper())
                system_parts.append(f"[{label}]\n{section.content}")

        system_block = "\n\n".join(system_parts)

        parts: list[str] = []
        parts.append(f"<|im_start|>system\n{system_block}<|im_end|>")

        if history_content:
            for line in history_content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[user]:"):
                    msg = line[len("[user]:"):].strip()
                    parts.append(f"<|im_start|>user\n{msg}<|im_end|>")
                elif line.startswith("[assistant]:"):
                    msg = line[len("[assistant]:"):].strip()
                    parts.append(f"<|im_start|>assistant\n{msg}<|im_end|>")

        parts.append(f"<|im_start|>user\n{user_content}<|im_end|>")
        parts.append("<|im_start|>assistant\n")

        return "\n".join(parts)

    def estimate_remaining_budget(
        self,
        system_prompt: str = "",
        character: Character | None = None,
    ) -> int:
        system_tokens = self._counter.count(system_prompt) if system_prompt else 0
        char_tokens = 0
        if character:
            char_tokens = self._counter.count(character.to_context_string())
        return self._max_context - self._max_response - system_tokens - char_tokens
