import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.dice import DiceResult, DiceRoller, RollContext, parse_notation
from src.core.exceptions import ValidationError


class TestParseNotation:
    def test_simple_d20(self) -> None:
        count, sides, modifier = parse_notation("d20")
        assert count == 1
        assert sides == 20
        assert modifier == 0

    def test_multiple_dice(self) -> None:
        count, sides, modifier = parse_notation("2d6")
        assert count == 2
        assert sides == 6
        assert modifier == 0

    def test_positive_modifier(self) -> None:
        count, sides, modifier = parse_notation("1d8+3")
        assert count == 1
        assert sides == 8
        assert modifier == 3

    def test_negative_modifier(self) -> None:
        count, sides, modifier = parse_notation("1d20-2")
        assert count == 1
        assert sides == 20
        assert modifier == -2

    def test_d100(self) -> None:
        count, sides, modifier = parse_notation("d100")
        assert count == 1
        assert sides == 100
        assert modifier == 0

    def test_case_insensitive(self) -> None:
        count, sides, _modifier = parse_notation("D20")
        assert count == 1
        assert sides == 20

    def test_invalid_notation(self) -> None:
        with pytest.raises(ValidationError):
            parse_notation("d30")

    def test_invalid_format(self) -> None:
        with pytest.raises(ValidationError):
            parse_notation("hello")

    def test_zero_dice(self) -> None:
        with pytest.raises(ValidationError):
            parse_notation("0d20")


class TestDiceRoller:
    def test_simple_d20(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20")
        assert isinstance(result, DiceResult)
        assert 1 <= result.total <= 20
        assert result.notation == "d20"
        assert result.modifier == 0
        assert len(result.components) == 1
        assert result.components[0].type == "d20"

    def test_2d6(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("2d6")
        assert 2 <= result.total <= 12
        assert result.components[0].count == 2
        assert len(result.components[0].rolls) == 2
        for roll in result.components[0].rolls:
            assert 1 <= roll <= 6

    def test_modifier_positive(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20+5")
        assert result.modifier == 5
        assert 6 <= result.total <= 25

    def test_modifier_negative(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20-3")
        assert result.modifier == -3
        assert -2 <= result.total <= 17

    def test_deterministic_with_seed(self) -> None:
        roller1 = DiceRoller(seed=123)
        roller2 = DiceRoller(seed=123)
        for _ in range(20):
            r1 = roller1.roll("d20")
            r2 = roller2.roll("d20")
            assert r1.total == r2.total

    def test_different_seeds_different_results(self) -> None:
        roller1 = DiceRoller(seed=1)
        roller2 = DiceRoller(seed=2)
        results1 = [roller1.roll("d20").total for _ in range(10)]
        results2 = [roller2.roll("d20").total for _ in range(10)]
        assert results1 != results2

    def test_roll_has_id(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20")
        assert result.id is not None
        assert len(result.id) > 0

    def test_roll_has_hash(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20")
        assert result.hash is not None
        assert len(result.hash) == 16

    def test_roll_has_timestamp(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20")
        assert result.timestamp is not None

    def test_roll_with_context(self, dice_roller: DiceRoller) -> None:
        ctx = RollContext(reason="attack", actor_id="char_001", session_id="sess_001")
        result = dice_roller.roll("d20", context=ctx)
        assert result.context.reason == "attack"
        assert result.context.actor_id == "char_001"

    def test_to_dict(self, dice_roller: DiceRoller) -> None:
        result = dice_roller.roll("d20+3")
        d = result.to_dict()
        assert d["notation"] == "d20+3"
        assert d["modifier"] == 3
        assert "components" in d
        assert "timestamp" in d
        assert "hash" in d

    @given(
        count=st.integers(min_value=1, max_value=10),
        sides=st.sampled_from([4, 6, 8, 10, 12, 20, 100]),
        modifier=st.integers(min_value=-10, max_value=10),
    )
    @settings(max_examples=50)
    def test_valid_ranges(self, count: int, sides: int, modifier: int) -> None:
        roller = DiceRoller(seed=42)
        sign = "+" if modifier >= 0 else ""
        notation = f"{count}d{sides}{sign}{modifier}"
        result = roller.roll(notation)
        min_roll = count * 1 + modifier
        max_roll = count * sides + modifier
        assert min_roll <= result.total <= max_roll


class TestDiceRollerAdvantage:
    def test_advantage(self) -> None:
        roller = DiceRoller(seed=42)
        result = roller.roll_with_advantage("d20")
        assert 1 <= result.total <= 20

    def test_disadvantage(self) -> None:
        roller = DiceRoller(seed=42)
        result = roller.roll_with_disadvantage("d20")
        assert 1 <= result.total <= 20


class TestDiceRollerDropLowest:
    def test_4d6_drop_lowest(self) -> None:
        roller = DiceRoller(seed=42)
        result = roller.roll_drop_lowest(count=4, sides=6, drop=1)
        assert len(result.components[0].rolls) == 3
        assert len(result.components[0].dropped) == 1
        assert 3 <= result.total <= 18

    def test_drop_too_many(self) -> None:
        roller = DiceRoller(seed=42)
        with pytest.raises(ValidationError):
            roller.roll_drop_lowest(count=2, sides=6, drop=2)
