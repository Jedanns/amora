from typing import Any


class RPGEngineError(Exception):
    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.context = context or {}
        super().__init__(message)


class ValidationError(RPGEngineError):
    pass


class StateError(RPGEngineError):
    pass


class InvariantViolationError(StateError):
    def __init__(self, invariant: str, details: str = "") -> None:
        super().__init__(
            f"Invariant violation: {invariant}",
            context={"invariant": invariant, "details": details},
        )


class LLMError(RPGEngineError):
    pass


class LLMConnectionError(LLMError):
    pass


class LLMGenerationError(LLMError):
    pass


class LLMContentFilterError(LLMError):
    pass


class LoreError(RPGEngineError):
    pass


class LoreInjectionError(LoreError):
    pass


class LoreCycleError(LoreError):
    pass


class InventoryError(RPGEngineError):
    pass


class InsufficientSpaceError(InventoryError):
    pass


class WeightLimitExceededError(InventoryError):
    pass


class ItemNotFoundError(InventoryError):
    pass


class CharacterError(RPGEngineError):
    pass


class QuestError(RPGEngineError):
    pass


class SessionError(RPGEngineError):
    pass
