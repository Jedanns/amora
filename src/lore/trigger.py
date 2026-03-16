from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.lore.entry import LorebookEntry, LoreCondition


@dataclass(frozen=True)
class TriggerResult:
    entry_id: str
    matched: bool
    matched_keys: tuple[str, ...]
    match_type: str
    score: float = 1.0


def match_exact(
    text: str,
    keys: list[str],
    case_sensitive: bool = False,
) -> list[str]:
    search_text = text if case_sensitive else text.lower()
    matched: list[str] = []
    for key in keys:
        search_key = key if case_sensitive else key.lower()
        if search_key in search_text:
            matched.append(key)
    return matched


def match_regex(text: str, patterns: list[str]) -> list[str]:
    matched: list[str] = []
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(pattern)
        except re.error:
            continue
    return matched


def match_fuzzy(
    text: str,
    keys: list[str],
    threshold: float = 0.85,
) -> list[str]:
    matched: list[str] = []
    text_lower = text.lower()
    for key in keys:
        key_lower = key.lower()
        if len(key_lower) < 3:
            continue
        ratio = _levenshtein_ratio(text_lower, key_lower)
        if ratio >= threshold:
            matched.append(key)
    return matched


def _levenshtein_ratio(text: str, key: str) -> float:
    best_ratio = 0.0
    key_len = len(key)
    if key_len == 0:
        return 0.0

    for i in range(len(text) - key_len + 1):
        window = text[i : i + key_len]
        distance = _levenshtein_distance(window, key)
        ratio = 1.0 - (distance / max(len(window), key_len))
        if ratio > best_ratio:
            best_ratio = ratio

    return best_ratio


def _levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def check_conditions(
    conditions: list[LoreCondition],
    game_state: dict[str, object],
) -> bool:
    if not conditions:
        return True

    for condition in conditions:
        state_value = game_state.get(condition.key)
        if state_value is None:
            return False

        expected = condition.value
        op = condition.operator

        if (
            (op == "eq" and state_value != expected)
            or (op == "ne" and state_value == expected)
            or (
                op == "gt"
                and not (
                    isinstance(state_value, (int, float)) and state_value > expected
                )
            )
            or (
                op == "lt"
                and not (
                    isinstance(state_value, (int, float)) and state_value < expected
                )
            )
            or (
                op == "gte"
                and not (
                    isinstance(state_value, (int, float)) and state_value >= expected
                )
            )
            or (
                op == "lte"
                and not (
                    isinstance(state_value, (int, float)) and state_value <= expected
                )
            )
        ):
            return False
        elif (
            op == "contains"
            and isinstance(state_value, str)
            and isinstance(expected, str)
        ):
            if expected.lower() not in state_value.lower():
                return False
        elif (
            op == "in" and isinstance(state_value, list) and expected not in state_value
        ):
            return False

    return True


def check_probability(trigger_chance: int) -> bool:
    if trigger_chance >= 100:
        return True
    if trigger_chance <= 0:
        return False
    return random.randint(1, 100) <= trigger_chance


class TriggerEngine:
    def __init__(self, fuzzy_threshold: float = 0.85) -> None:
        self._fuzzy_threshold = fuzzy_threshold

    def evaluate(
        self,
        entry: LorebookEntry,
        text: str,
        messages: list[str] | None = None,
        game_state: dict[str, object] | None = None,
    ) -> TriggerResult:
        if not entry.enabled:
            return TriggerResult(
                entry_id=entry.id, matched=False, matched_keys=(), match_type="disabled"
            )

        if entry.is_constant:
            return TriggerResult(
                entry_id=entry.id,
                matched=True,
                matched_keys=(),
                match_type="constant",
                score=1.0,
            )

        scan_text = self._build_scan_text(text, messages, entry.scan_depth)

        if game_state and not check_conditions(entry.conditions, game_state):
            return TriggerResult(
                entry_id=entry.id,
                matched=False,
                matched_keys=(),
                match_type="condition_failed",
            )

        all_matched: list[str] = []
        match_type = "none"

        exact_primary = match_exact(scan_text, entry.keys, entry.case_sensitive)
        if exact_primary:
            all_matched.extend(exact_primary)
            match_type = "exact_primary"

        if not all_matched and entry.secondary_keys:
            exact_secondary = match_exact(
                scan_text, entry.secondary_keys, entry.case_sensitive
            )
            if exact_secondary:
                all_matched.extend(exact_secondary)
                match_type = "exact_secondary"

        regex_matched = match_regex(scan_text, entry.regex_keys)
        if regex_matched:
            all_matched.extend(regex_matched)
            match_type = match_type if match_type != "none" else "regex"

        if not all_matched and entry.keys:
            fuzzy_matched = match_fuzzy(scan_text, entry.keys, self._fuzzy_threshold)
            if fuzzy_matched:
                all_matched.extend(fuzzy_matched)
                match_type = "fuzzy"

        if not all_matched:
            return TriggerResult(
                entry_id=entry.id,
                matched=False,
                matched_keys=(),
                match_type="none",
            )

        if entry.use_probability and not check_probability(entry.trigger_chance):
            return TriggerResult(
                entry_id=entry.id,
                matched=False,
                matched_keys=tuple(all_matched),
                match_type="probability_miss",
            )

        score = self._calculate_score(match_type, len(all_matched), entry)

        return TriggerResult(
            entry_id=entry.id,
            matched=True,
            matched_keys=tuple(all_matched),
            match_type=match_type,
            score=score,
        )

    def _build_scan_text(
        self,
        current_text: str,
        messages: list[str] | None,
        scan_depth: int,
    ) -> str:
        parts = [current_text]
        if messages and scan_depth > 0:
            recent = messages[-scan_depth:]
            parts.extend(recent)
        return "\n".join(parts)

    def _calculate_score(
        self,
        match_type: str,
        match_count: int,
        entry: LorebookEntry,
    ) -> float:
        base_scores = {
            "constant": 1.0,
            "exact_primary": 0.95,
            "regex": 0.9,
            "exact_secondary": 0.8,
            "fuzzy": 0.6,
        }
        base = base_scores.get(match_type, 0.5)
        count_bonus = min(0.1, match_count * 0.02)
        priority_bonus = entry.priority / 10000.0
        return min(1.0, base + count_bonus + priority_bonus)
