"""Usage aggregation: totals, fallbacks, ranges, breakdowns, owner isolation."""

import asyncio
import json
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.app.generation_service as generation_service
from backend.app.generation_models import GenerationRequest
from backend.app.generation_service import GenerationManager
from backend.app.generation_store import GenerationStore
from backend.app.model_provider import ProviderUsage
from backend.app.storage import Store
from backend.app.usage_routes import build_usage_router
from backend.app.usage_service import analytics, summarize


def _row(status="completed", metrics=None, *, created_at=None, provider="openrouter/test-model", model="test-model"):
    return {"id": "gen_1", "owner_id": "local", "session_id": "s1", "status": status,
            "provider": provider, "model": model,
            "payload": json.dumps({"metrics": metrics or {}}), "created_at": created_at or time.time()}


def test_exact_and_legacy_rows_combine_with_source_counts():
    rows = [
        _row(metrics={"promptTokens": 100, "completionTokens": 50, "totalTokens": 150,
                      "usageSource": "exact", "usageProvider": "openrouter", "providerCost": 0.002}),
        _row(metrics={"outputCharacters": 400, "estimatedOutputTokens": 100}),
    ]
    summary = summarize(rows, range_key="all")
    assert summary["totals"]["totalTokens"] == 250
    assert summary["totals"]["promptTokens"] == 100
    assert summary["totals"]["completionTokens"] == 150
    assert summary["totals"]["generations"] == 2
    assert summary["totals"]["exactGenerations"] == 1
    assert summary["totals"]["estimatedGenerations"] == 1


def test_cost_is_exact_only_when_provider_reported():
    exact_without_cost = summarize([_row(metrics={"promptTokens": 10, "completionTokens": 5, "totalTokens": 15,
                                                          "usageSource": "exact", "usageProvider": "openai"})], range_key="all")
    assert exact_without_cost["totals"]["providerCost"] == 0
    assert exact_without_cost["totals"]["costIsExact"] is False
    with_cost = summarize([_row(metrics={"promptTokens": 10, "completionTokens": 5, "totalTokens": 15,
                                                  "usageSource": "exact", "usageProvider": "openrouter", "providerCost": 0.001})], range_key="all")
    assert with_cost["totals"]["providerCost"] == 0.001
    assert with_cost["totals"]["costIsExact"] is True


def test_non_completed_and_malformed_rows_excluded():
    rows = [_row(status="failed", metrics={"promptTokens": 1, "completionTokens": 1, "totalTokens": 2, "usageSource": "exact"}),
            {"id": "bad", "status": "completed", "payload": "not-json", "provider": "x", "model": "y", "created_at": time.time()}]
    summary = summarize(rows, range_key="all")
    assert summary["totals"]["generations"] == 1
    assert summary["totals"]["totalTokens"] == 0


def test_range_filtering_and_day_filling():
    recent = _row(metrics={"promptTokens": 5, "completionTokens": 5, "totalTokens": 10, "usageSource": "exact"})
    old = _row(metrics={"promptTokens": 5, "completionTokens": 5, "totalTokens": 10, "usageSource": "exact"},
               created_at=time.time() - 20 * 86400)
    week = summarize([recent, old], range_key="7d")
    assert week["totals"]["generations"] == 1
    assert len(week["byDay"]) == 7
    month = summarize([recent, old], range_key="30d")
    assert month["totals"]["generations"] == 2
    assert len(month["byDay"]) == 30


def test_model_and_provider_breakdowns_sorted():
    rows = [
        _row(metrics={"promptTokens": 1, "completionTokens": 1, "totalTokens": 2, "usageSource": "exact", "usageProvider": "openrouter"},
             provider="openrouter/a", model="a"),
        _row(metrics={"promptTokens": 4, "completionTokens": 4, "totalTokens": 8, "usageSource": "exact", "usageProvider": "openai"},
             provider="openai/b", model="b"),
        _row(metrics={"promptTokens": 4, "completionTokens": 4, "totalTokens": 8, "usageSource": "exact", "usageProvider": "openai"},
             provider="openai/b", model="b"),
    ]
    summary = summarize(rows, range_key="all")
    assert summary["byModel"][0]["model"] == "b"
    assert summary["byModel"][0]["totalTokens"] == 16
    assert summary["byProvider"][0]["provider"] == "openai"
    assert summary["byProvider"][0]["generations"] == 2


def _seed_completed(store: Store, owner: str, total_tokens: int, cost: float | None = None):
    records = GenerationStore(store)
    request = {"mode": "ask", "message": "hi", "gear": "Guided", "expectedRevision": 1}
    record = records.create(owner, "session-1", request, f"key-{owner}-{total_tokens}-{time.time_ns()}", "openrouter/m", "m")
    records.transition(record["id"], "preparing")
    records.transition(record["id"], "streaming")
    records.transition(record["id"], "finalizing")
    metrics: dict = {"promptTokens": total_tokens - 3, "completionTokens": 3, "totalTokens": total_tokens,
                     "usageSource": "exact", "usageProvider": "openrouter"}
    if cost is not None:
        metrics["providerCost"] = cost
    records.update_metrics(record["id"], metrics)
    records.transition(record["id"], "completed", result={"revision": 1})
    return record


def test_api_returns_owner_scoped_aggregates(tmp_path):
    store = Store(tmp_path / "usage.db")
    _seed_completed(store, "alice", 100, 0.001)
    _seed_completed(store, "alice", 50)
    _seed_completed(store, "bob", 9999, 9.99)
    app = FastAPI()
    app.include_router(build_usage_router(lambda: store))
    client = TestClient(app)
    alice = client.get("/v1/usage/summary?range=all", headers={"X-Dev-Learner-Id": "alice"})
    assert alice.status_code == 200, alice.text
    body = alice.json()
    assert body["totals"]["totalTokens"] == 150
    assert body["totals"]["generations"] == 2
    assert body["totals"]["providerCost"] == 0.001
    bob = client.get("/v1/usage/summary?range=all", headers={"X-Dev-Learner-Id": "bob"})
    assert bob.json()["totals"]["totalTokens"] == 9999
    assert bob.json()["totals"]["generations"] == 1
    store.close()


def test_api_empty_usage_returns_zeros(tmp_path):
    store = Store(tmp_path / "usage-empty.db")
    app = FastAPI()
    app.include_router(build_usage_router(lambda: store))
    client = TestClient(app)
    response = client.get("/v1/usage/summary?range=all", headers={"X-Dev-Learner-Id": "nobody"})
    assert response.status_code == 200
    assert response.json()["totals"] == {"totalTokens": 0, "promptTokens": 0, "completionTokens": 0, "generations": 0,
                                         "exactGenerations": 0, "estimatedGenerations": 0, "providerCost": 0, "costIsExact": False}
    store.close()


class _StubStreamProvider:
    provider_name = "openrouter/stub-model"
    model = "stub-model"

    def __init__(self, usage: ProviderUsage | None):
        self._usage = usage
        self.last_usage: ProviderUsage | None = None

    async def stream_text(self, prompt: str, max_tokens: int = 4000, **kwargs):
        yield "A complete lesson body with enough characters to differ from token counts."
        self.last_usage = self._usage


class _StubJourney:
    def __init__(self, *args, **kwargs):
        pass

    def prepare_stream(self, owner, session_id, request):
        return {"prompt": "p", "sources": [], "actionId": "a", "title": "T"}

    def commit_stream(self, connection, owner, prepared, request, body):
        return SimpleNamespace(id="lesson_1"), {"revision": 1, "sessionId": "session-1"}


def test_streaming_run_persists_exact_usage_and_completed_event(tmp_path, monkeypatch):
    monkeypatch.setattr(generation_service, "JourneyService", _StubJourney)
    store = Store(tmp_path / "usage-run.db")
    provider = _StubStreamProvider(ProviderUsage(prompt_tokens=40, completion_tokens=10, total_tokens=50, cost=0.0007))
    manager = GenerationManager(store, provider)
    request = GenerationRequest(mode="ask", message="hi", gear="Guided", expectedRevision=1)

    async def scenario():
        record = manager.records.create("local", "session-1", request.model_dump(mode="json", by_alias=True),
                                        "usage-key-1", provider.provider_name, provider.model)
        await manager._run(record["id"], "local", request)
        return record["id"]

    generation_id = asyncio.run(scenario())
    record = manager.records.get("local", generation_id)
    assert record["status"] == "completed"
    metrics = record["metrics"]
    assert metrics["promptTokens"] == 40
    assert metrics["completionTokens"] == 10
    assert metrics["totalTokens"] == 50
    assert metrics["providerCost"] == 0.0007
    assert metrics["usageSource"] == "exact"
    assert metrics["estimatedOutputTokens"] >= 1  # fallback estimate still recorded
    completed = [event for event in manager.buffer.get_after_sequence(generation_id, 0) if event.type == "generation.completed"]
    assert completed and completed[0].data["usage"]["totalTokens"] == 50
    assert completed[0].data["usage"]["usageSource"] == "exact"
    summary = summarize([dict(manager.records.get("local", generation_id), payload=json.dumps({"metrics": metrics}),
                              status="completed", provider=record["provider"], model=record["model"],
                              created_at=time.time())], range_key="all")
    assert summary["totals"]["totalTokens"] == 50
    store.close()


def test_streaming_run_without_provider_usage_falls_back_to_estimate(tmp_path, monkeypatch):
    monkeypatch.setattr(generation_service, "JourneyService", _StubJourney)
    store = Store(tmp_path / "usage-run-est.db")
    provider = _StubStreamProvider(None)
    manager = GenerationManager(store, provider)
    request = GenerationRequest(mode="ask", message="hi", gear="Guided", expectedRevision=1)

    async def scenario():
        record = manager.records.create("local", "session-1", request.model_dump(mode="json", by_alias=True),
                                        "usage-key-2", provider.provider_name, provider.model)
        await manager._run(record["id"], "local", request)
        return record["id"]

    generation_id = asyncio.run(scenario())
    metrics = manager.records.get("local", generation_id)["metrics"]
    assert metrics["usageSource"] == "estimated"
    assert "promptTokens" not in metrics
    assert metrics["estimatedOutputTokens"] >= 1
    store.close()


def _analytics_row(*, mode="ask", model="m", provider="openrouter/m", session="s1", total=10, cost=None, age_days=1):
    metrics = {"promptTokens": total - 2, "completionTokens": 2, "totalTokens": total,
               "usageSource": "exact", "usageProvider": provider.split("/")[0]}
    if cost is not None:
        metrics["providerCost"] = cost
    row = _row(metrics=metrics, provider=provider, model=model)
    row["mode"] = mode
    row["session_id"] = session
    row["created_at"] = time.time() - age_days * 86400
    return row


def test_analytics_series_shares_and_points_align_with_days():
    rows = [_analytics_row(mode="ask", total=90), _analytics_row(mode="learn", total=10)]
    result = analytics(rows, range_key="7d", dimension="mode")
    assert result["range"] == "7d" and result["dimension"] == "mode"
    assert len(result["days"]) == 7
    assert [entry["key"] for entry in result["series"]] == ["Ask", "Learn"]
    assert result["series"][0]["sharePct"] == 90.0
    assert abs(sum(entry["sharePct"] for entry in result["series"]) - 100.0) < 0.01
    for entry in result["series"]:
        assert len(entry["points"]) == 7
        assert sum(entry["points"]) == entry["totalTokens"]
        assert len(entry["genPoints"]) == 7
        assert sum(entry["genPoints"]) == entry["generations"]
    assert sum(day["totalTokens"] for day in result["days"]) == 100


def test_analytics_dimension_model_and_provider():
    rows = [_analytics_row(model="a", provider="openrouter/a", total=30),
            _analytics_row(model="b", provider="openai/b", total=70)]
    by_model = analytics(rows, range_key="30d", dimension="model")
    assert [entry["key"] for entry in by_model["series"]] == ["b", "a"]
    assert len(by_model["days"]) == 30
    by_provider = analytics(rows, range_key="30d", dimension="provider")
    assert {entry["key"] for entry in by_provider["series"]} == {"openai", "openrouter"}


def test_analytics_top_sessions_ranked_with_titles_and_model_split():
    rows = [_analytics_row(session="s-big", total=60, model="a", cost=0.002),
            _analytics_row(session="s-big", total=40, model="b"),
            _analytics_row(session="s-small", total=5, model="a")]
    result = analytics(rows, range_key="7d", dimension="mode",
                       session_titles={"s-big": "Volcanoes"}, session_limit=5)
    top = result["topSessions"]
    assert [entry["sessionId"] for entry in top] == ["s-big", "s-small"]
    assert top[0]["title"] == "Volcanoes"
    assert top[1]["title"] == "s-small"
    assert top[0]["providerCost"] == 0.002 and top[0]["costIsExact"] is True
    assert top[1]["costIsExact"] is False
    assert {entry["model"] for entry in top[0]["byModel"]} == {"a", "b"}
    assert top[0]["lastActive"] is not None


def test_analytics_excludes_out_of_range_and_failed():
    rows = [_analytics_row(age_days=20), _row(status="failed", metrics={"promptTokens": 1, "totalTokens": 1, "usageSource": "exact"})]
    result = analytics(rows, range_key="7d", dimension="mode")
    assert result["totals"]["generations"] == 0
    assert result["series"] == [] and result["topSessions"] == []


def test_analytics_endpoint_is_owner_scoped(tmp_path):
    store = Store(tmp_path / "usage-analytics.db")
    _seed_completed(store, "alice", 100, 0.001)
    _seed_completed(store, "alice", 50)
    _seed_completed(store, "bob", 9999, 9.99)
    app = FastAPI()
    app.include_router(build_usage_router(lambda: store))
    client = TestClient(app)
    response = client.get("/v1/usage/analytics?range=7d&dimension=mode", headers={"X-Dev-Learner-Id": "alice"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totals"]["totalTokens"] == 150
    assert body["dimension"] == "mode"
    assert len(body["days"]) == 7
    assert body["topSessions"] and body["topSessions"][0]["totalTokens"] == 150
    bob = client.get("/v1/usage/analytics?range=7d&dimension=model", headers={"X-Dev-Learner-Id": "bob"})
    assert bob.json()["totals"]["totalTokens"] == 9999
    assert client.get("/v1/usage/analytics?range=7d&dimension=bogus", headers={"X-Dev-Learner-Id": "alice"}).status_code == 422
    store.close()
