import json

import httpx
import pytest

import backend.app.model_provider as model_provider
from backend.app.model_provider import ImageInput, ModelProviderError, OpenRouterLessonProvider, configured_lesson_provider


def test_openrouter_provider_parses_structured_lesson(monkeypatch):
    provider = OpenRouterLessonProvider("test-key", "openai/gpt-4o", None, None)
    response = httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"message": {"content": json.dumps({"blocks": [
        {"kind": "lesson", "heading": "Core idea", "body": "A careful explanation."},
        {"kind": "check", "heading": "Try it", "body": "What would change?"},
    ]})}}]})
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    blocks = provider.generate(graph=None, concept=type("Concept", (), {"title": "Volcanoes"})(), context=None, plan=type("Plan", (), {"strategy": type("S", (), {"value": "direct_explanation"})(), "representation_sequence": ["intuition"]})(), intent=type("I", (), {"value": "teach"})())
    assert [block.kind for block in blocks] == ["explanation", "check"]


def test_openrouter_provider_rejects_invalid_blocks(monkeypatch):
    provider = OpenRouterLessonProvider("test-key", "openai/gpt-4o", None, None)
    response = httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"message": {"content": '{"blocks": []}'}}]})
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    with pytest.raises(ModelProviderError):
        provider.generate(graph=None, concept=type("Concept", (), {"title": "Volcanoes"})(), context=None, plan=type("Plan", (), {"strategy": type("S", (), {"value": "direct_explanation"})(), "representation_sequence": ["intuition"]})(), intent=type("I", (), {"value": "teach"})())


def test_openrouter_provider_uses_explanation_for_unknown_presentation_kind(monkeypatch):
    provider = OpenRouterLessonProvider("test-key", "openai/gpt-4o", None, None)
    response = httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"message": {"content": json.dumps({"blocks": [
        {"kind": "concept", "heading": "Core idea", "body": "A careful explanation."},
        {"kind": "check", "heading": "Try it", "body": "What would change?"},
    ]})}}]})
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    blocks = provider.generate(graph=None, concept=type("Concept", (), {"title": "Volcanoes"})(), context=None, plan=type("Plan", (), {"strategy": type("S", (), {"value": "direct_explanation"})(), "representation_sequence": ["intuition"]})(), intent=type("I", (), {"value": "teach"})())
    assert blocks[0].kind == "explanation"


def test_openrouter_requires_a_key(monkeypatch):
    monkeypatch.setenv("AI_TUTOR_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(model_provider, "load_dotenv", lambda *args, **kwargs: False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        configured_lesson_provider()


def test_free_nemotron_accepts_long_fenced_json_without_response_format(monkeypatch):
    provider = OpenRouterLessonProvider("test-key", "nvidia/nemotron-3-ultra-550b-a55b:free", None, None)
    content = json.dumps({"blocks": [{"kind": "explanation", "heading": f"Section {i}", "body": "A detailed paragraph."} for i in range(10)]})
    def post(*args, **kwargs):
        assert "response_format" not in kwargs["json"]
        assert kwargs["json"]["reasoning"] == {"enabled": False}
        return httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"finish_reason": "stop", "message": {"content": f"```json\n{content}\n```"}}]})
    monkeypatch.setattr(httpx, "post", post)
    assert len(provider._complete("Write a full lesson", 3600)) == 10


@pytest.mark.parametrize("kind", [[], {}, None])
def test_provider_rejects_non_string_kinds(monkeypatch, kind):
    content = json.dumps({"blocks": [{"kind": kind, "heading": "Heading", "body": "Body"}] * 2})
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"message": {"content": content}}]}))
    with pytest.raises(ModelProviderError, match="invalid lesson block"):
        OpenRouterLessonProvider("key", "model", None, None)._complete("prompt", 1000)


def test_provider_rejects_truncated_output(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"finish_reason": "length", "message": {"content": '{"blocks":'}}]}))
    with pytest.raises(ModelProviderError, match="response limit"):
        OpenRouterLessonProvider("key", "model", None, None)._complete("prompt", 1000)


def test_provider_never_uses_reasoning_as_final_answer(monkeypatch):
    hidden = json.dumps({"blocks": [{"kind": "explanation", "heading": "Private", "body": "Internal reasoning must never become an answer."}]})
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices": [{"message": {"content": None, "reasoning_content": hidden}}]}))
    with pytest.raises(ModelProviderError):
        OpenRouterLessonProvider("key", "model", None, None)._complete("prompt", 1000)


def test_responses_incomplete_is_not_presented_as_a_complete_explanation(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"status": "incomplete", "output_text": '{"blocks":[]}'}))
    with pytest.raises(ModelProviderError, match="response limit"):
        OpenRouterLessonProvider.openai("key", "model")._complete("prompt", 1000)


@pytest.mark.parametrize("status, message", [(402, "credits"), (429, "free request limit"), (404, "available endpoint")])
def test_provider_reports_actionable_errors(monkeypatch, status, message):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(status, request=httpx.Request("POST", "https://example.test")))
    with pytest.raises(ModelProviderError, match=message):
        OpenRouterLessonProvider("key", "model", None, None)._complete("prompt", 1000)


def test_openai_streaming_payload_contains_real_image_input():
    provider = OpenRouterLessonProvider.openai("key", "gpt-4.1-mini")
    payload = provider.streaming_payload("Explain the diagram", 500, [ImageInput("image/png", b"png", "diagram")])
    content = payload["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "Explain the diagram"}
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


def test_openrouter_streaming_payload_contains_real_image_input():
    provider = OpenRouterLessonProvider("key", "vision-model", None, None)
    payload = provider.streaming_payload("Explain the photo", 500, [ImageInput("image/jpeg", b"jpeg", "photo")])
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
