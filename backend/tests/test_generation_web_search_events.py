"""End-to-end verification that web search tool lifecycle events are emitted during generation streaming."""
from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.generation_models import GenerationRequest
from backend.app.generation_service import GenerationManager
from backend.app.graph_generator import GraphGenerator
from backend.app.models import TopicScope, utc_now
from backend.app.session_models import LearningSession
from backend.app.storage import Store
from backend.app.web_evidence.models import ProviderSearchHit, SourceClassification


class MockWebSearchProvider:
    provider_name = "test-provider"
    model = "test-model"

    def __init__(self):
        self.proposal_called = 0

    def complete_json(self, prompt: str, max_tokens: int = 4000, *, allow_text: bool = False):
        self.proposal_called += 1
        if self.proposal_called == 1:
            # First call is for tool loop proposal
            return {
                "action": "tool_calls",
                "toolCalls": [
                    {
                        "name": "search_web_evidence",
                        "arguments": {
                            "query": "superconductors at room temperature",
                            "intent": "definition",
                        },
                        "idempotencyKey": "idem-web-test-1",
                    }
                ],
            }
        # Second call in tool loop: answer
        return {"action": "answer", "toolCalls": []}

    async def stream_text(self, prompt: str, max_tokens: int = 3500, *, images=None):
        yield "## Explanation\n"
        yield "Superconductors carry electrical current with zero resistance."


@pytest.mark.asyncio
async def test_generation_streams_tool_lifecycle_events(tmp_path, monkeypatch):
    # Enable web evidence in environment
    monkeypatch.setenv("AI_TUTOR_WEB_EVIDENCE", "1")
    monkeypatch.setenv("AI_TUTOR_WEB_PROVIDER", "fake")
    monkeypatch.setenv("AI_TUTOR_ENV", "development")
    monkeypatch.setenv("AI_TUTOR_DEV_IDENTITY", "true")

    db_path = tmp_path / f"test-{uuid4().hex}.db"
    store = Store(db_path)

    scope = TopicScope(
        id="scope-gen-web",
        topic="Physics",
        resolved_meaning="Physics",
        objective="Learn superconductivity",
        depth="introductory",
        created_at=utc_now(),
    )
    graph = GraphGenerator().generate(scope)
    store.save_scope(scope)
    store.save_graph(graph)

    session = LearningSession(
        id="session-gen-web",
        learner_id="test-learner",
        graph_id=graph.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    store.save_session(session)

    provider = MockWebSearchProvider()
    manager = GenerationManager(store, provider)

    req = GenerationRequest(
        mode="ask",
        message="What are superconductors according to latest research?",
        gear="Guided",
        expectedRevision=1,
    )

    record = manager.create("test-learner", session.id, req, "test-idem-key")
    gen_id = record["id"]

    # Collect events from the live generator
    collected = []
    async for event in manager.events("test-learner", gen_id, 0):
        collected.append(event)
        if event.type in {"generation.completed", "generation.error", "generation.cancelled"}:
            break

    event_types = [e.type for e in collected]
    assert "generation.started" in event_types
    assert "tool.started" in event_types
    assert "tool.completed" in event_types
    assert "generation.context_ready" in event_types
    assert "lesson.block_started" in event_types
    assert "text.delta" in event_types
    assert "lesson.block_completed" in event_types
    assert "generation.completed" in event_types

    # Verify tool.started payload
    tool_started = next(e for e in collected if e.type == "tool.started")
    assert tool_started.data["tool"] == "search_web_evidence"
    assert "superconductors" in tool_started.data["query"]

    # Verify tool.completed payload
    tool_completed = next(e for e in collected if e.type == "tool.completed")
    assert tool_completed.data["tool"] == "search_web_evidence"
    assert "sourceCount" in tool_completed.data

    # Verify order: tool.started before tool.completed, tool.completed before generation.context_ready
    started_idx = event_types.index("tool.started")
    completed_idx = event_types.index("tool.completed")
    context_ready_idx = event_types.index("generation.context_ready")
    assert started_idx < completed_idx < context_ready_idx

    store.close()
