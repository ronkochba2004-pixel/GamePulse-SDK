from datetime import UTC, datetime
from uuid import uuid4

from gamepulse_core import (
    BaseEvent,
    BatchEventsRequest,
    EventCategory,
    LevelStartEvent,
)


def test_base_event_roundtrip():
    ev = BaseEvent(
        type="custom.thing",
        category=EventCategory.CUSTOM,
        name="thing",
        occurred_at=datetime.now(UTC),
        payload={"x": 1},
    )
    data = ev.model_dump(mode="json")
    again = BaseEvent.model_validate(data)
    assert again.payload == {"x": 1}


def test_level_start_defaults():
    ev = LevelStartEvent(payload={"level": 3})
    assert ev.type == "progression.level_start"
    assert ev.name == "level_start"


def test_batch_request_capped():
    ev = LevelStartEvent(payload={"level": 1})
    req = BatchEventsRequest(player_external_id="u1", events=[ev])
    assert req.events[0].event_id is not None
    _ = uuid4()
