from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from src.core.exceptions import ValidationError

VALID_DICE = frozenset({4, 6, 8, 10, 12, 20, 100})
NOTATION_PATTERN = re.compile(
    r"^(?P<count>\d+)?d(?P<sides>100|20|12|10|8|6|4)(?P<mod>[+-]\d+)?$"
)


class RandomSource(Protocol):
    def roll(self, sides: int) -> int: ...


class DefaultRandom:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def roll(self, sides: int) -> int:
        return self._rng.randint(1, sides)


@dataclass(frozen=True)
class DiceComponent:
    type: str
    count: int
    rolls: tuple[int, ...]
    dropped: tuple[int, ...] = ()

    @property
    def total(self) -> int:
        return sum(self.rolls)


@dataclass(frozen=True)
class RollContext:
    reason: str = ""
    actor_id: str = ""
    target_id: str = ""
    skill: str = ""
    session_id: str = ""


@dataclass(frozen=True)
class DiceResult:
    id: str
    notation: str
    components: tuple[DiceComponent, ...]
    modifier: int
    total: int
    context: RollContext
    timestamp: datetime
    hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "notation": self.notation,
            "components": [
                {
                    "type": c.type,
                    "count": c.count,
                    "rolls": list(c.rolls),
                    "dropped": list(c.dropped),
                }
                for c in self.components
            ],
            "modifier": self.modifier,
            "total": self.total,
            "context": {
                "reason": self.context.reason,
                "actor_id": self.context.actor_id,
                "target_id": self.context.target_id,
                "skill": self.context.skill,
                "session_id": self.context.session_id,
            },
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash,
        }


def parse_notation(notation: str) -> tuple[int, int, int]:
    match = NOTATION_PATTERN.match(notation.strip().lower())
    if not match:
        raise ValidationError(
            f"Invalid dice notation: '{notation}'. "
            f"Expected format: [N]d{{4,6,8,10,12,20,100}}[+/-M]"
        )
    count = int(match.group("count") or "1")
    sides = int(match.group("sides"))
    mod_str = match.group("mod")
    modifier = int(mod_str) if mod_str else 0

    if sides not in VALID_DICE:
        raise ValidationError(f"Unsupported dice type: d{sides}")
    if count < 1 or count > 100:
        raise ValidationError(f"Dice count must be between 1 and 100, got {count}")
    if abs(modifier) > 1000:
        raise ValidationError(
            f"Modifier must be between -1000 and 1000, got {modifier}"
        )

    return count, sides, modifier


def _compute_hash(
    notation: str, rolls: list[int], modifier: int, total: int, roll_id: str
) -> str:
    payload = json.dumps(
        {
            "id": roll_id,
            "notation": notation,
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class DiceRoller:
    def __init__(self, seed: int | None = None) -> None:
        self._source: RandomSource = DefaultRandom(seed)

    def roll(
        self,
        notation: str,
        context: RollContext | None = None,
    ) -> DiceResult:
        count, sides, modifier = parse_notation(notation)
        ctx = context or RollContext()

        individual_rolls = [self._source.roll(sides) for _ in range(count)]
        component = DiceComponent(
            type=f"d{sides}",
            count=count,
            rolls=tuple(individual_rolls),
        )
        total = sum(individual_rolls) + modifier
        roll_id = uuid4().hex
        roll_hash = _compute_hash(notation, individual_rolls, modifier, total, roll_id)

        return DiceResult(
            id=roll_id,
            notation=notation,
            components=(component,),
            modifier=modifier,
            total=total,
            context=ctx,
            timestamp=datetime.now(UTC),
            hash=roll_hash,
        )

    def roll_with_advantage(
        self,
        notation: str,
        context: RollContext | None = None,
    ) -> DiceResult:
        r1 = self.roll(notation, context)
        r2 = self.roll(notation, context)
        return r1 if r1.total >= r2.total else r2

    def roll_with_disadvantage(
        self,
        notation: str,
        context: RollContext | None = None,
    ) -> DiceResult:
        r1 = self.roll(notation, context)
        r2 = self.roll(notation, context)
        return r1 if r1.total <= r2.total else r2

    def roll_drop_lowest(
        self,
        count: int,
        sides: int,
        drop: int = 1,
        modifier: int = 0,
        context: RollContext | None = None,
    ) -> DiceResult:
        if drop >= count:
            raise ValidationError(f"Cannot drop {drop} dice from {count} dice")
        ctx = context or RollContext()

        individual_rolls = [self._source.roll(sides) for _ in range(count)]
        sorted_rolls = sorted(individual_rolls)
        dropped = tuple(sorted_rolls[:drop])
        kept = tuple(sorted_rolls[drop:])

        component = DiceComponent(
            type=f"d{sides}",
            count=count,
            rolls=kept,
            dropped=dropped,
        )
        total = sum(kept) + modifier
        notation = f"{count}d{sides}dl{drop}"
        if modifier:
            notation += f"{'+' if modifier > 0 else ''}{modifier}"

        roll_id = uuid4().hex
        roll_hash = _compute_hash(notation, individual_rolls, modifier, total, roll_id)

        return DiceResult(
            id=roll_id,
            notation=notation,
            components=(component,),
            modifier=modifier,
            total=total,
            context=ctx,
            timestamp=datetime.now(UTC),
            hash=roll_hash,
        )
