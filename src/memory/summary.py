from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from src.llm.tokens import estimate_tokens

if TYPE_CHECKING:
    from src.llm.gateway import GenerationResult, LLMProvider

logger = logging.getLogger(__name__)

SUMMARY_THRESHOLD_DEFAULT = 50
SUMMARY_EVERY_DEFAULT = 30
SUMMARY_MAX_TOKENS = 500
SUMMARY_TEMPERATURE = 0.3


class FactType(StrEnum):
    CHARACTER_RELATION = "character_relation"
    LOCATION_VISITED = "location_visited"
    ITEM_ACQUIRED = "item_acquired"
    QUEST_PROGRESS = "quest_progress"
    DEATH = "death"
    STATE_CHANGE = "state_change"
    PLAYER_DECISION = "player_decision"
    NPC_INTERACTION = "npc_interaction"


@dataclass(frozen=True)
class KeyFact:
    id: str = field(default_factory=lambda: f"fact_{uuid4().hex[:8]}")
    type: FactType = FactType.STATE_CHANGE
    content: str = ""
    confidence: float = 1.0
    source_message_id: str = ""
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "confidence": self.confidence,
            "source_message_id": self.source_message_id,
            "extracted_at": self.extracted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> KeyFact:
        fact_type = FactType(str(data.get("type", "state_change")))
        extracted = data.get("extracted_at")
        if isinstance(extracted, str):
            extracted_dt = datetime.fromisoformat(extracted)
        else:
            extracted_dt = datetime.now(UTC)
        return cls(
            id=str(data.get("id", f"fact_{uuid4().hex[:8]}")),
            type=fact_type,
            content=str(data.get("content", "")),
            confidence=float(data.get("confidence", 1.0)),  # type: ignore[arg-type]
            source_message_id=str(data.get("source_message_id", "")),
            extracted_at=extracted_dt,
        )


@dataclass
class Summary:
    text: str
    key_facts: list[KeyFact] = field(default_factory=list)
    message_range: tuple[str, str] = ("", "")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    previous_summary_id: str = ""
    token_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "key_facts": [f.to_dict() for f in self.key_facts],
            "message_range_start": self.message_range[0],
            "message_range_end": self.message_range[1],
            "created_at": self.created_at.isoformat(),
            "previous_summary_id": self.previous_summary_id,
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Summary:
        created = data.get("created_at")
        if isinstance(created, str):
            created_dt = datetime.fromisoformat(created)
        else:
            created_dt = datetime.now(UTC)
        facts_data = data.get("key_facts", [])
        facts = [KeyFact.from_dict(f) for f in facts_data] if isinstance(facts_data, list) else []  # type: ignore[arg-type]
        return cls(
            text=str(data.get("text", "")),
            key_facts=facts,
            message_range=(
                str(data.get("message_range_start", "")),
                str(data.get("message_range_end", "")),
            ),
            created_at=created_dt,
            previous_summary_id=str(data.get("previous_summary_id", "")),
            token_count=int(data.get("token_count", 0)),  # type: ignore[arg-type]
        )


SUMMARY_PROMPT_TEMPLATE = (
    "Tu es un assistant spécialisé dans le résumé de sessions de jeu de rôle.\n"
    "Résume les messages suivants de manière concise, en gardant les informations importantes:\n"
    "- Actions clés du joueur\n"
    "- Événements importants\n"
    "- Changements d'état (PV, inventaire, quêtes)\n"
    "- Interactions PNJ notables\n"
    "- Lieux visités\n\n"
)

SUMMARY_WITH_PREVIOUS_TEMPLATE = (
    "Voici le résumé précédent de la session:\n"
    "{previous_summary}\n\n"
    "Continue le résumé en intégrant les nouveaux messages:\n\n"
)

FACT_EXTRACTION_PROMPT = (
    "Extrais les faits importants du texte suivant sous forme de liste.\n"
    "Chaque fait doit être une ligne commençant par un type entre crochets:\n"
    "[character_relation] pour les relations entre personnages\n"
    "[location_visited] pour les lieux visités\n"
    "[item_acquired] pour les objets obtenus\n"
    "[quest_progress] pour l'avancement des quêtes\n"
    "[death] pour les morts\n"
    "[state_change] pour les changements d'état du monde\n"
    "[player_decision] pour les décisions importantes du joueur\n"
    "[npc_interaction] pour les interactions PNJ notables\n\n"
    "Texte:\n{text}\n\n"
    "Faits:\n"
)


class Summarizer:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        summary_threshold: int = SUMMARY_THRESHOLD_DEFAULT,
        summary_every: int = SUMMARY_EVERY_DEFAULT,
        max_summary_tokens: int = SUMMARY_MAX_TOKENS,
    ) -> None:
        self._llm = llm_provider
        self._threshold = summary_threshold
        self._every = summary_every
        self._max_tokens = max_summary_tokens

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def summary_interval(self) -> int:
        return self._every

    def should_summarize(self, message_count: int) -> bool:
        return (
            message_count >= self._threshold
            and message_count % self._every == 0
        )

    async def summarize(
        self,
        messages: list[dict[str, str]],
        previous_summary: str | None = None,
    ) -> Summary:
        if self._llm is not None:
            return await self._summarize_with_llm(messages, previous_summary)
        return self._summarize_heuristic(messages, previous_summary)

    async def _summarize_with_llm(
        self,
        messages: list[dict[str, str]],
        previous_summary: str | None = None,
    ) -> Summary:
        from src.llm.gateway import GenerationParams

        prompt = self._build_summary_prompt(messages, previous_summary)
        params = GenerationParams(
            max_tokens=self._max_tokens,
            temperature=SUMMARY_TEMPERATURE,
        )

        result: GenerationResult = await self._llm.generate(prompt, params)  # type: ignore[union-attr]
        summary_text = result.text.strip()

        key_facts = await self._extract_facts_with_llm(summary_text)

        first_id = messages[0].get("id", "") if messages else ""
        last_id = messages[-1].get("id", "") if messages else ""

        return Summary(
            text=summary_text,
            key_facts=key_facts,
            message_range=(first_id, last_id),
            token_count=estimate_tokens(summary_text),
        )

    async def _extract_facts_with_llm(self, summary_text: str) -> list[KeyFact]:
        from src.llm.gateway import GenerationParams

        prompt = FACT_EXTRACTION_PROMPT.format(text=summary_text)
        params = GenerationParams(
            max_tokens=300,
            temperature=0.2,
        )

        try:
            result = await self._llm.generate(prompt, params)  # type: ignore[union-attr]
            return self._parse_facts(result.text)
        except Exception:
            logger.exception("Failed to extract facts with LLM")
            return []

    def _summarize_heuristic(
        self,
        messages: list[dict[str, str]],
        previous_summary: str | None = None,
    ) -> Summary:
        important_messages: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            msg_type = msg.get("type", msg.get("role", ""))
            if msg_type in ("roll", "action"):
                important_messages.append(content)
            elif msg_type == "assistant" and len(content) > 100:
                important_messages.append(content[:200] + "...")
            elif msg_type == "user":
                important_messages.append(f"Joueur: {content[:100]}")

        summary_parts: list[str] = []
        if previous_summary:
            summary_parts.append(previous_summary)

        if important_messages:
            summary_parts.append(
                "Événements récents:\n" + "\n".join(f"- {m}" for m in important_messages[-10:])
            )

        summary_text = "\n\n".join(summary_parts) if summary_parts else "Début de session."

        key_facts = self._extract_facts_heuristic(messages)

        first_id = messages[0].get("id", "") if messages else ""
        last_id = messages[-1].get("id", "") if messages else ""

        return Summary(
            text=summary_text,
            key_facts=key_facts,
            message_range=(first_id, last_id),
            token_count=estimate_tokens(summary_text),
        )

    def _extract_facts_heuristic(self, messages: list[dict[str, str]]) -> list[KeyFact]:
        facts: list[KeyFact] = []
        for msg in messages:
            content = msg.get("content", "")
            msg_id = msg.get("id", "")

            if re.search(r"(?:visite|arrive|entre dans|se rend)", content, re.IGNORECASE):
                facts.append(KeyFact(
                    type=FactType.LOCATION_VISITED,
                    content=content[:150],
                    confidence=0.7,
                    source_message_id=msg_id,
                ))

            if re.search(r"(?:obtient|ramasse|reçoit|prend|acquiert)", content, re.IGNORECASE):
                facts.append(KeyFact(
                    type=FactType.ITEM_ACQUIRED,
                    content=content[:150],
                    confidence=0.7,
                    source_message_id=msg_id,
                ))

            if re.search(r"(?:quête|mission|objectif)", content, re.IGNORECASE):
                facts.append(KeyFact(
                    type=FactType.QUEST_PROGRESS,
                    content=content[:150],
                    confidence=0.6,
                    source_message_id=msg_id,
                ))

            if re.search(r"(?:meurt|tué|mort|éliminé)", content, re.IGNORECASE):
                facts.append(KeyFact(
                    type=FactType.DEATH,
                    content=content[:150],
                    confidence=0.8,
                    source_message_id=msg_id,
                ))

        return facts

    def _build_summary_prompt(
        self,
        messages: list[dict[str, str]],
        previous_summary: str | None = None,
    ) -> str:
        parts: list[str] = [SUMMARY_PROMPT_TEMPLATE]

        if previous_summary:
            parts.append(
                SUMMARY_WITH_PREVIOUS_TEMPLATE.format(previous_summary=previous_summary)
            )

        messages_text = "\n".join(
            f"[{msg.get('role', 'system')}]: {msg.get('content', '')}"
            for msg in messages
        )
        parts.append(f"Messages:\n{messages_text}\n\nRésumé:")
        return "\n".join(parts)

    def _parse_facts(self, text: str) -> list[KeyFact]:
        facts: list[KeyFact] = []
        pattern = re.compile(r"\[(\w+)\]\s*(.+)")

        for line in text.strip().split("\n"):
            match = pattern.match(line.strip())
            if match:
                raw_type = match.group(1)
                content = match.group(2).strip()
                try:
                    fact_type = FactType(raw_type)
                except ValueError:
                    fact_type = FactType.STATE_CHANGE
                facts.append(KeyFact(
                    type=fact_type,
                    content=content,
                    confidence=0.8,
                ))

        return facts
