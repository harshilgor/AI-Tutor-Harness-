import asyncio

import pytest

from backend.app.generation_models import GenerationRequest
from backend.app.generation_service import EventBuffer
from backend.app.generation_store import GenerationStore
from backend.app.storage import Store


def request(message="Explain probability"):
    return GenerationRequest(mode="ask", message=message, gear="Guided", expectedRevision=1).model_dump(mode="json", by_alias=True)


def test_generation_idempotency_and_lifecycle(tmp_path):
    store = Store(tmp_path / "generation.db")
    records = GenerationStore(store)
    first = records.create("local", "session-1", request(), "same-key", "test", "test-model")
    duplicate = records.create("local", "session-1", request(), "same-key", "test", "test-model")
    assert duplicate["id"] == first["id"] and first["status"] == "queued"
    records.transition(first["id"], "preparing")
    records.update_metrics(first["id"], {"applicationTtftSeconds": 0.25})
    records.transition(first["id"], "streaming")
    records.transition(first["id"], "finalizing")
    records.transition(first["id"], "completed", result={"revision": 2})
    assert records.get("local", first["id"])["result"]["revision"] == 2
    assert GenerationStore.descriptor(records.get("local", first["id"])).metrics["applicationTtftSeconds"] == 0.25
    with pytest.raises(Exception):
        records.create("local", "session-1", request("Different request"), "same-key", "test", "test-model")
    store.close()


def test_event_buffer_replays_in_sequence_and_supports_duplicate_safe_consumers():
    async def scenario():
        buffer = EventBuffer()
        one = await buffer.publish("gen-1", "generation.started")
        two = await buffer.publish("gen-1", "text.delta", {"text": "Hello"})
        replay = []
        async for event in buffer.observe("gen-1", 0, True):
            replay.append(event)
        assert [event.sequence for event in replay] == [one.sequence, two.sequence]
        # A reconnect at sequence one sees only the new delta.
        reconnect = []
        async for event in buffer.observe("gen-1", one.sequence, True):
            reconnect.append(event)
        assert [event.sequence for event in reconnect] == [two.sequence]
    asyncio.run(scenario())


def test_cancel_request_becomes_a_terminal_cancelled_generation(tmp_path):
    store = Store(tmp_path / "cancel.db")
    records = GenerationStore(store)
    created = records.create("local", "session-1", request(), "cancel-key", "test", "test-model")
    records.transition(created["id"], "preparing")
    requested = records.request_cancel("local", created["id"])
    assert requested["status"] == "cancel_requested" and requested["cancellationRequested"] is True
    records.transition(created["id"], "cancelled", error_code="CANCELLED")
    assert records.get("local", created["id"])["status"] == "cancelled"
    store.close()
