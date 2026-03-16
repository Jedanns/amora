from src.lore.entry import LorebookCategory, LorebookEntry, LoreCondition
from src.lore.trigger import (
    TriggerEngine,
    check_conditions,
    check_probability,
    match_exact,
    match_fuzzy,
    match_regex,
)


class TestMatchExact:
    def test_simple_match(self) -> None:
        result = match_exact("I visit the tavern.", ["tavern"])
        assert "tavern" in result

    def test_no_match(self) -> None:
        result = match_exact("I visit the shop.", ["tavern"])
        assert len(result) == 0

    def test_case_insensitive(self) -> None:
        result = match_exact("I visit the TAVERN.", ["tavern"], case_sensitive=False)
        assert "tavern" in result

    def test_case_sensitive(self) -> None:
        result = match_exact("I visit the TAVERN.", ["tavern"], case_sensitive=True)
        assert len(result) == 0

    def test_multiple_keys(self) -> None:
        result = match_exact(
            "I drink beer at the tavern.", ["tavern", "beer", "dragon"]
        )
        assert "tavern" in result
        assert "beer" in result
        assert "dragon" not in result

    def test_partial_match(self) -> None:
        result = match_exact("excalibur is legendary", ["excalibur"])
        assert "excalibur" in result


class TestMatchRegex:
    def test_simple_regex(self) -> None:
        result = match_regex("I enter the taverne.", [r"tavern[e]?"])
        assert len(result) == 1

    def test_no_match(self) -> None:
        result = match_regex("Nothing here.", [r"tavern[e]?"])
        assert len(result) == 0

    def test_invalid_regex_skipped(self) -> None:
        result = match_regex("Some text.", [r"[invalid", r"text"])
        assert "text" in result
        assert r"[invalid" not in result

    def test_complex_pattern(self) -> None:
        result = match_regex("The dragon attacks!", [r"dragon\s+attacks?"])
        assert len(result) == 1


class TestMatchFuzzy:
    def test_exact_match_high_score(self) -> None:
        result = match_fuzzy("I found excalibur!", ["excalibur"], threshold=0.85)
        assert "excalibur" in result

    def test_typo_match(self) -> None:
        result = match_fuzzy("I found excalibir!", ["excalibur"], threshold=0.8)
        assert "excalibur" in result

    def test_no_match_too_different(self) -> None:
        result = match_fuzzy("I found a sword.", ["excalibur"], threshold=0.85)
        assert len(result) == 0

    def test_short_keys_ignored(self) -> None:
        result = match_fuzzy("ab text", ["ab"], threshold=0.85)
        assert len(result) == 0


class TestCheckConditions:
    def test_no_conditions(self) -> None:
        assert check_conditions([], {})

    def test_eq_condition_pass(self) -> None:
        conditions = [LoreCondition(type="state", key="location", value="tavern")]
        assert check_conditions(conditions, {"location": "tavern"})

    def test_eq_condition_fail(self) -> None:
        conditions = [LoreCondition(type="state", key="location", value="tavern")]
        assert not check_conditions(conditions, {"location": "forest"})

    def test_missing_key(self) -> None:
        conditions = [LoreCondition(type="state", key="nonexistent", value="x")]
        assert not check_conditions(conditions, {})

    def test_gt_condition(self) -> None:
        conditions = [LoreCondition(type="state", key="level", operator="gt", value=5)]
        assert check_conditions(conditions, {"level": 10})
        assert not check_conditions(conditions, {"level": 3})

    def test_contains_condition(self) -> None:
        conditions = [
            LoreCondition(type="state", key="name", operator="contains", value="dragon")
        ]
        assert check_conditions(conditions, {"name": "Dragon Slayer"})
        assert not check_conditions(conditions, {"name": "Goblin Killer"})

    def test_multiple_conditions_all_must_pass(self) -> None:
        conditions = [
            LoreCondition(type="state", key="location", value="dungeon"),
            LoreCondition(type="state", key="level", operator="gte", value=5),
        ]
        assert check_conditions(conditions, {"location": "dungeon", "level": 5})
        assert not check_conditions(conditions, {"location": "dungeon", "level": 3})


class TestCheckProbability:
    def test_always(self) -> None:
        assert check_probability(100)

    def test_never(self) -> None:
        assert not check_probability(0)


class TestTriggerEngine:
    def _make_entry(self, **kwargs: object) -> LorebookEntry:
        defaults = {"name": "Test Entry", "content": "Content"}
        defaults.update(kwargs)
        return LorebookEntry(**defaults)  # type: ignore[arg-type]

    def test_constant_always_triggers(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(category=LorebookCategory.CONSTANT)
        result = engine.evaluate(entry, "any text")
        assert result.matched
        assert result.match_type == "constant"

    def test_disabled_entry_never_triggers(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(enabled=False, keys=["test"])
        result = engine.evaluate(entry, "test")
        assert not result.matched
        assert result.match_type == "disabled"

    def test_exact_primary_key_match(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(keys=["tavern", "auberge"])
        result = engine.evaluate(entry, "I go to the tavern.")
        assert result.matched
        assert "tavern" in result.matched_keys
        assert result.match_type == "exact_primary"

    def test_secondary_key_match(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(
            keys=["dragon ivre"],
            secondary_keys=["boire", "biere"],
        )
        result = engine.evaluate(entry, "Je veux boire une biere.")
        assert result.matched
        assert result.match_type == "exact_secondary"

    def test_regex_key_match(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(
            keys=[],
            regex_keys=[r"dragon\s+\w+"],
        )
        result = engine.evaluate(entry, "The dragon attacks!")
        assert result.matched

    def test_no_match(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(keys=["excalibur"])
        result = engine.evaluate(entry, "I buy a potion.")
        assert not result.matched

    def test_condition_filter(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(
            keys=["secret"],
            conditions=[LoreCondition(type="state", key="has_key", value=True)],
        )
        result_pass = engine.evaluate(
            entry, "I search for secret", game_state={"has_key": True}
        )
        assert result_pass.matched

        result_fail = engine.evaluate(
            entry, "I search for secret", game_state={"has_key": False}
        )
        assert not result_fail.matched

    def test_scan_depth_with_messages(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(keys=["tavern"], scan_depth=3)
        messages = ["I was in the forest.", "Then the tavern.", "Now in the castle."]
        result = engine.evaluate(entry, "What do I see?", messages=messages)
        assert result.matched

    def test_score_ranking(self) -> None:
        engine = TriggerEngine()
        entry = self._make_entry(keys=["tavern"], priority=800)
        result = engine.evaluate(entry, "I go to the tavern.")
        assert result.score > 0.5
