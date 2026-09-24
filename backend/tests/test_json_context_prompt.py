import json
from types import SimpleNamespace

import pytest

from backend.app.json_context_prompt import bounded_json_prompt
from backend.app.model_provider import ModelProviderError


def test_required_json_context_is_retained_and_optional_history_is_omitted():
    provider = SimpleNamespace(context_input_budget_tokens=1000)
    prompt = bounded_json_prompt(provider, "Return JSON.", {
        "schema": {"type": "object"},
        "response": "my answer",
        "prior": "p" * 10000,
    }, required={"schema", "response"})
    payload = json.loads(prompt.split("\n", 1)[1])
    assert payload == {"schema": {"type": "object"}, "response": "my answer"}


def test_required_json_context_fails_when_too_large():
    provider = SimpleNamespace(context_input_budget_tokens=500)
    with pytest.raises(ModelProviderError, match="Narrow the source or request"):
        bounded_json_prompt(provider, "Return JSON.", {"response": "x" * 10000}, required={"response"})
