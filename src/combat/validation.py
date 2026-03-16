from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

from src.character.manager import CharacterManager
from src.core.exceptions import InvariantViolationError
from src.inventory.manager import Inventory

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    violations: list[str] = field(default_factory=list)

    def add_violation(self, message: str) -> None:
        self.violations.append(message)
        self.valid = False


ValidationRule = Callable[
    [CharacterManager, dict[str, Inventory]],
    list[str],
]


def rule_hp_non_negative(
    characters: CharacterManager,
    _inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char in characters.list_active():
        if char.hp.current < 0:
            violations.append(
                f"Character {char.name} ({char.id}) has negative HP: {char.hp.current}"
            )
    return violations


def rule_hp_not_exceeding_max(
    characters: CharacterManager,
    _inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char in characters.list_active():
        if char.hp.current > char.hp.effective_max:
            violations.append(
                f"Character {char.name} ({char.id}) HP ({char.hp.current}) "
                f"exceeds max ({char.hp.effective_max})"
            )
    return violations


def rule_mana_non_negative(
    characters: CharacterManager,
    _inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char in characters.list_active():
        if char.mana.current < 0:
            violations.append(
                f"Character {char.name} ({char.id}) has negative mana: {char.mana.current}"
            )
    return violations


def rule_level_in_range(
    characters: CharacterManager,
    _inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char in characters.list_active():
        if char.level < 1 or char.level > 20:
            violations.append(
                f"Character {char.name} ({char.id}) has invalid level: {char.level}"
            )
    return violations


def rule_inventory_weight(
    _characters: CharacterManager,
    inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char_id, inv in inventories.items():
        if inv.total_weight > inv.config.max_weight:
            violations.append(
                f"Inventory of {char_id} exceeds weight limit: "
                f"{inv.total_weight:.1f}/{inv.config.max_weight:.1f}"
            )
    return violations


def rule_inventory_slots(
    _characters: CharacterManager,
    inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char_id, inv in inventories.items():
        if inv.slot_count > inv.config.max_slots:
            violations.append(
                f"Inventory of {char_id} exceeds slot limit: "
                f"{inv.slot_count}/{inv.config.max_slots}"
            )
    return violations


def rule_experience_non_negative(
    characters: CharacterManager,
    _inventories: dict[str, Inventory],
) -> list[str]:
    violations: list[str] = []
    for char in characters.list_active():
        if char.experience < 0:
            violations.append(
                f"Character {char.name} ({char.id}) has negative XP: {char.experience}"
            )
    return violations


DEFAULT_RULES: list[ValidationRule] = [
    rule_hp_non_negative,
    rule_hp_not_exceeding_max,
    rule_mana_non_negative,
    rule_level_in_range,
    rule_inventory_weight,
    rule_inventory_slots,
    rule_experience_non_negative,
]


class StateValidator:
    def __init__(
        self,
        characters: CharacterManager,
        inventories: dict[str, Inventory],
        rules: list[ValidationRule] | None = None,
        strict: bool = False,
    ) -> None:
        self._characters = characters
        self._inventories = inventories
        self._rules = rules if rules is not None else list(DEFAULT_RULES)
        self._strict = strict

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def validate(self) -> ValidationResult:
        result = ValidationResult(valid=True)

        for rule in self._rules:
            violations = rule(self._characters, self._inventories)
            for v in violations:
                result.add_violation(v)

        if result.violations:
            logger.warning(
                "state_validation_failed",
                violation_count=len(result.violations),
                violations=result.violations,
            )

            if self._strict:
                raise InvariantViolationError(
                    "State validation failed",
                    details="; ".join(result.violations),
                )

        return result

    def is_valid(self) -> bool:
        return self.validate().valid
