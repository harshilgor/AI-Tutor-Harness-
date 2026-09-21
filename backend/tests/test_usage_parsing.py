"""Provider usage parsing: exact OpenRouter/OpenAI shapes, streaming capture, safe fallbacks."""

import asyncio
import json

import httpx

from backend.app.model_provider import (
    OpenRouterLessonProvider,
    normalize_usage,
    usage_metrics,
)


def _response(payload: dict) -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json=payload)


def _lesson_content(blocks: int = 1) -> str:
    return json.dumps({"blocks": [{"kind": "explanation", "heading": "H", "body": "B"} for _ in range(blocks)]})


def test_normalize_openrouter_usage_with_cost():
    usage = normalize_usage({"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200, "cost": 0.0012}, is_openai=False)
    assert usage is not None
    assert (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens, usage.cost) == (120, 80, 200, 0.0012)


def test_normalize_openai_responses_usage():
    usage = normalize_usage({"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}, is_openai=True)
    assert usage is not None
    assert (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens) == (50, 25, 75)
    assert usage.cost is None


def test_normalize_usage_absent_or_invalid_returns_none():
    assert normalize_usage(None, is_openai=False) is None
    assert normalize_usage({}, is_openai=False) is None
    assert normalize_usage({"prompt_tokens": -1}, is_openai=False) is None
    assert normalize_usage({"prompt_tokens": "many"}, is_openai=False) is None


def test_normalize_usage_derives_total_when_missing():
    usage = normalize_usage({"prompt_tokens": 10, "completion_tokens": 5}, is_openai=False)
    assert usage is not None and usage.total_tokens == 15


def test_complete_json_records_openrouter_usage(monkeypatch):
    provider = OpenRouterLessonProvider("key", "model", None, None)
    payload = {"choices": [{"finish_reason": "stop", "message": {"content": _lesson_content()}}],
               "usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140, "cost": 0.002}}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: _response(payload))
    provider._complete("prompt", 500)
    assert provider.last_usage is not None
    assert provider.last_usage.total_tokens == 140
    assert provider.last_usage.cost == 0.002


def test_complete_json_records_openai_usage(monkeypatch):
    provider = OpenRouterLessonProvider.openai("key", "gpt-test")
    payload = {"output": [{"type": "message", "content": [{"type": "output_text", "text": _lesson_content()}]}],
               "usage": {"input_tokens": 60, "output_tokens": 30, "total_tokens": 90}}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: _response(payload))
    provider._complete("prompt", 500)
    assert provider.last_usage is not None
    assert (provider.last_usage.prompt_tokens, provider.last_usage.completion_tokens) == (60, 30)


def test_complete_json_without_usage_leaves_last_usage_none(monkeypatch):
    provider = OpenRouterLessonProvider("key", "model", None, None)
    payload = {"choices": [{"finish_reason": "stop", "message": {"content": _lesson_content()}}]}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: _response(payload))
    provider._complete("prompt", 500)
    assert provider.last_usage is None


class _FakeStream:
    def __init__(self, lines: list[str]):
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class _FakeClient:
    def __init__(self, lines: list[str]):
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, *args, **kwargs):
        return _FakeStream(self.lines)


def _collect(provider) -> str:
    async def run():
        chunks = []
        async for chunk in provider.stream_text("prompt", 100):
            chunks.append(chunk)
        return "".join(chunks)

    return asyncio.run(run())


def test_streaming_openrouter_captures_final_usage(monkeypatch):
    provider = OpenRouterLessonProvider("key", "model", None, None)
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":3,"total_tokens":15,"cost":0.0004}}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _FakeClient(lines))
    assert _collect(provider) == "Hello"
    assert provider.last_usage is not None
    assert (provider.last_usage.prompt_tokens, provider.last_usage.completion_tokens, provider.last_usage.total_tokens) == (12, 3, 15)
    assert provider.last_usage.cost == 0.0004


def test_streaming_openai_captures_completed_usage(monkeypatch):
    provider = OpenRouterLessonProvider.openai("key", "gpt-test")
    lines = [
        'data: {"type":"response.output_text.delta","delta":"Hi"}',
        'data: {"type":"response.completed","response":{"usage":{"input_tokens":20,"output_tokens":7,"total_tokens":27}}}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _FakeClient(lines))
    assert _collect(provider) == "Hi"
    assert provider.last_usage is not None
    assert (provider.last_usage.prompt_tokens, provider.last_usage.completion_tokens, provider.last_usage.total_tokens) == (20, 7, 27)


def test_streaming_without_usage_leaves_last_usage_none(monkeypatch):
    provider = OpenRouterLessonProvider("key", "model", None, None)
    lines = ['data: {"choices":[{"delta":{"content":"Hi"}}]}', "data: [DONE]"]
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _FakeClient(lines))
    assert _collect(provider) == "Hi"
    assert provider.last_usage is None


def test_usage_metrics_fragment_marks_exact_provider():
    usage = normalize_usage({"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10, "cost": 0.001}, is_openai=False)
    fragment = usage_metrics(usage, provider="openrouter")
    assert fragment == {"promptTokens": 5, "completionTokens": 5, "totalTokens": 10,
                        "usageSource": "exact", "usageProvider": "openrouter", "providerCost": 0.001}
    assert usage_metrics(None, provider="openrouter") == {}
