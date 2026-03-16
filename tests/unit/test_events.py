import pytest

from src.core.events import EventBus, EventType, GameEvent


class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self) -> None:
        bus = EventBus()
        received: list[GameEvent] = []

        async def handler(event: GameEvent) -> None:
            received.append(event)

        bus.subscribe(EventType.DICE_ROLLED, handler)
        event = GameEvent(type=EventType.DICE_ROLLED, data={"total": 15})
        await bus.emit(event)

        assert len(received) == 1
        assert received[0].data["total"] == 15

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        bus = EventBus()
        received: list[GameEvent] = []

        async def handler(event: GameEvent) -> None:
            received.append(event)

        unsub = bus.subscribe(EventType.DICE_ROLLED, handler)
        unsub()

        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_multiple_handlers(self) -> None:
        bus = EventBus()
        count = 0

        async def handler1(event: GameEvent) -> None:
            nonlocal count
            count += 1

        async def handler2(event: GameEvent) -> None:
            nonlocal count
            count += 10

        bus.subscribe(EventType.DICE_ROLLED, handler1)
        bus.subscribe(EventType.DICE_ROLLED, handler2)

        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))
        assert count == 11

    @pytest.mark.asyncio
    async def test_global_handler(self) -> None:
        bus = EventBus()
        received: list[EventType] = []

        async def handler(event: GameEvent) -> None:
            received.append(event.type)

        bus.subscribe_all(handler)

        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))
        await bus.emit(GameEvent(type=EventType.CHARACTER_UPDATED))

        assert EventType.DICE_ROLLED in received
        assert EventType.CHARACTER_UPDATED in received

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash(self) -> None:
        bus = EventBus()

        async def bad_handler(event: GameEvent) -> None:
            raise ValueError("oops")

        async def good_handler(event: GameEvent) -> None:
            pass

        bus.subscribe(EventType.DICE_ROLLED, bad_handler)
        bus.subscribe(EventType.DICE_ROLLED, good_handler)

        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))

    @pytest.mark.asyncio
    async def test_event_has_id_and_timestamp(self) -> None:
        event = GameEvent(type=EventType.DICE_ROLLED)
        assert event.id is not None
        assert event.timestamp is not None

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        bus = EventBus()
        received: list[GameEvent] = []

        async def handler(event: GameEvent) -> None:
            received.append(event)

        bus.subscribe(EventType.DICE_ROLLED, handler)
        bus.clear()

        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_no_handlers_doesnt_crash(self) -> None:
        bus = EventBus()
        await bus.emit(GameEvent(type=EventType.DICE_ROLLED))
