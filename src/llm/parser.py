from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

logger = structlog.get_logger(__name__)

ACTION_PATTERN = re.compile(r"\[ACTION:(\w+):(\w+):(-?\d+)\]")


class ActionType(StrEnum):
    DAMAGE = "damage"
    HEAL = "heal"
    GIVE_ITEM = "give_item"
    REMOVE_ITEM = "remove_item"
    GIVE_XP = "give_xp"
    MOVE = "move"
    ADD_CONDITION = "add_condition"
    REMOVE_CONDITION = "remove_condition"
    DICE_ROLL = "dice_roll"
    QUEST_UPDATE = "quest_update"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Action:
    type: str
    target: str
    value: int
    raw: str = ""

    @property
    def action_type(self) -> ActionType:
        try:
            return ActionType(self.type)
        except ValueError:
            return ActionType.CUSTOM


@dataclass
class ParsedResponse:
    narrative: str
    actions: list[Action] = field(default_factory=list)
    raw: str = ""

    @property
    def has_actions(self) -> bool:
        return len(self.actions) > 0

    @property
    def action_count(self) -> int:
        return len(self.actions)

    def get_actions_by_type(self, action_type: str) -> list[Action]:
        return [a for a in self.actions if a.type == action_type]


SANITIZE_PATTERNS = [
    re.compile(r"<think>.*?</think>", re.DOTALL),
    re.compile(r"<think>.*", re.DOTALL),
    re.compile(r"<system>.*?</system>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<\|.*?\|>"),
    re.compile(r"\[INST\].*?\[/INST\]", re.DOTALL),
    re.compile(r"<(history|user|assistant|brok|scene|scène|context|prompt|input|output|response)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE),
    re.compile(r"</(history|user|assistant|brok|scene|scène|context|prompt|input|output|response)\s*>", re.IGNORECASE),
    re.compile(r"<(history|user|assistant|brok|scene|scène|context|prompt|input|output|response)\b[^>]*/?\s*>", re.IGNORECASE),
]

MARKDOWN_HEADER_PATTERN = re.compile(r"^#{1,3}\s+.*$", re.MULTILINE)

META_TRAIL_PATTERNS = [
    re.compile(r"\n\s*\(Remarque\b.*$", re.DOTALL | re.IGNORECASE),
    re.compile(r"\n\s*\(Note\b.*$", re.DOTALL | re.IGNORECASE),
    re.compile(r"\n\s*Qu['\u2019]est-ce que tu fais\s*\??.*$", re.DOTALL | re.IGNORECASE),
    re.compile(r"\n\s*Que fais-tu\s*\??.*$", re.DOTALL | re.IGNORECASE),
    re.compile(r"\n\s*Que faites-vous\s*\??.*$", re.DOTALL | re.IGNORECASE),
    re.compile(r"\n\s*Qu['\u2019]allez-vous faire\s*\??.*$", re.DOTALL | re.IGNORECASE),
]


class ResponseParser:
    def __init__(
        self,
        strip_whitespace: bool = True,
        sanitize: bool = True,
    ) -> None:
        self._strip_whitespace = strip_whitespace
        self._sanitize = sanitize

    def parse(self, raw_response: str) -> ParsedResponse:
        text = raw_response
        if self._sanitize:
            text = self._sanitize_response(text)

        actions = self._extract_actions(text)
        narrative = ACTION_PATTERN.sub("", text)

        if self._strip_whitespace:
            narrative = self._clean_narrative(narrative)

        return ParsedResponse(
            narrative=narrative,
            actions=actions,
            raw=raw_response,
        )

    def _extract_actions(self, text: str) -> list[Action]:
        actions: list[Action] = []
        for match in ACTION_PATTERN.finditer(text):
            action_type = match.group(1).lower()
            target = match.group(2).lower()
            try:
                value = int(match.group(3))
            except ValueError:
                continue

            actions.append(
                Action(
                    type=action_type,
                    target=target,
                    value=value,
                    raw=match.group(0),
                )
            )

        return actions

    def _sanitize_response(self, text: str) -> str:
        for pattern in SANITIZE_PATTERNS:
            text = pattern.sub("", text)
        text = re.sub(r"</?[a-zA-Zà-ÿÀ-Ÿ_][\w-]*\s*/?\s*>", "", text)
        text = MARKDOWN_HEADER_PATTERN.sub("", text)
        for pattern in META_TRAIL_PATTERNS:
            text = pattern.sub("", text)
        return text

    def _clean_narrative(self, text: str) -> str:
        lines = text.split("\n")
        cleaned_lines: list[str] = []
        prev_empty = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not prev_empty:
                    cleaned_lines.append("")
                prev_empty = True
            else:
                cleaned_lines.append(stripped)
                prev_empty = False

        result = "\n".join(cleaned_lines).strip()
        return result
