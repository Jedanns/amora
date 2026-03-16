from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from src.llm.tokens import TokenCounter, estimate_tokens

if TYPE_CHECKING:
    from src.character.models import Character
    from src.lore.entry import LorebookEntry

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    name: str = ""

    @property
    def token_estimate(self) -> int:
        return estimate_tokens(self.content) + 4


@dataclass
class PromptSections:
    system: str = ""
    character: str = ""
    lore: str = ""
    history: str = ""
    user_input: str = ""

    def to_parts(self) -> list[str]:
        parts: list[str] = []
        if self.system:
            parts.append(f"### INSTRUCTIONS\n{self.system}")
        if self.character:
            parts.append(f"### PERSONNAGE\n{self.character}")
        if self.lore:
            parts.append(f"### CONTEXTE DU MONDE\n{self.lore}")
        if self.history:
            parts.append(f"### HISTORIQUE\n{self.history}")
        if self.user_input:
            parts.append(f"### JOUEUR\n{self.user_input}")
        return parts


@dataclass
class PromptBuildResult:
    prompt: str
    sections: PromptSections
    total_tokens: int
    budget_remaining: int
    lore_entries_included: int
    history_messages_included: int
    truncated: bool = False


DEFAULT_SYSTEM_PROMPT = (
    "Tu es le narrateur d'un jeu de rôle textuel interactif. "
    "Tu décris les scènes de manière vivante et immersive. "
    "Tu réagis aux actions du joueur de manière cohérente avec le monde et les règles du jeu. "
    "Tu peux inclure des actions structurées dans ta réponse sous la forme [ACTION:type:cible:valeur]. "
    "Par exemple: [ACTION:damage:player:15] pour infliger 15 dégâts au joueur."
)


class PromptBuilder:
    def __init__(
        self,
        max_context_tokens: int = 16384,
        max_response_tokens: int = 512,
        system_prompt: str | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._max_context = max_context_tokens
        self._max_response = max_response_tokens
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._counter = token_counter or TokenCounter()

    @property
    def available_budget(self) -> int:
        system_tokens = self._counter.count(self._system_prompt)
        return self._max_context - self._max_response - system_tokens

    def build(
        self,
        user_input: str,
        character: Character | None = None,
        lore_entries: list[LorebookEntry] | None = None,
        conversation_history: list[Message] | None = None,
        extra_context: str = "",
    ) -> PromptBuildResult:
        sections = PromptSections(system=self._system_prompt)
        system_tokens = self._counter.count(self._system_prompt)
        remaining = self._max_context - self._max_response - system_tokens
        truncated = False
        lore_count = 0
        history_count = 0

        user_tokens = self._counter.count(user_input)
        remaining -= user_tokens
        sections.user_input = user_input

        if character:
            char_text = self._format_character(character)
            char_tokens = self._counter.count(char_text)
            if char_tokens <= remaining:
                sections.character = char_text
                remaining -= char_tokens
            else:
                truncated = True

        if extra_context:
            extra_tokens = self._counter.count(extra_context)
            if extra_tokens <= remaining:
                sections.character += (
                    f"\n\n{extra_context}" if sections.character else extra_context
                )
                remaining -= extra_tokens

        if lore_entries:
            lore_text, lore_count, lore_tokens = self._format_lore(
                lore_entries, remaining
            )
            if lore_text:
                sections.lore = lore_text
                remaining -= lore_tokens
                if lore_count < len(lore_entries):
                    truncated = True

        if conversation_history:
            history_text, history_count, hist_tokens = self._format_history(
                conversation_history, remaining
            )
            if history_text:
                sections.history = history_text
                remaining -= hist_tokens
                if history_count < len(conversation_history):
                    truncated = True

        parts = sections.to_parts()
        prompt = "\n\n".join(parts)
        total_tokens = self._counter.count(prompt)

        return PromptBuildResult(
            prompt=prompt,
            sections=sections,
            total_tokens=total_tokens,
            budget_remaining=remaining,
            lore_entries_included=lore_count,
            history_messages_included=history_count,
            truncated=truncated,
        )

    def _format_character(self, character: Character) -> str:
        return character.to_context_string()

    def _format_lore(
        self,
        entries: list[LorebookEntry],
        budget: int,
    ) -> tuple[str, int, int]:
        sorted_entries = sorted(entries, key=lambda e: e.priority, reverse=True)

        included: list[str] = []
        used_tokens = 0
        count = 0

        for entry in sorted_entries:
            text = entry.to_injection_text()
            tokens = self._counter.count(text)
            if used_tokens + tokens <= budget:
                included.append(text)
                used_tokens += tokens
                count += 1
            elif entry.truncatable:
                space = budget - used_tokens
                if space > entry.min_tokens and space > 10:
                    truncated_text = self._counter.truncate_to_budget(text, space)
                    included.append(truncated_text)
                    used_tokens += self._counter.count(truncated_text)
                    count += 1
                    break
            else:
                continue

        return "\n\n".join(included), count, used_tokens

    def _format_history(
        self,
        messages: list[Message],
        budget: int,
    ) -> tuple[str, int, int]:
        reversed_msgs = list(reversed(messages))
        included: list[Message] = []
        used_tokens = 0

        for msg in reversed_msgs:
            tokens = msg.token_estimate
            if used_tokens + tokens <= budget:
                included.append(msg)
                used_tokens += tokens
            else:
                break

        included.reverse()

        lines: list[str] = []
        for msg in included:
            prefix = msg.name or msg.role
            lines.append(f"[{prefix}]: {msg.content}")

        return "\n".join(lines), len(included), used_tokens
