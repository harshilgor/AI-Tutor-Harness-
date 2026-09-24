from types import SimpleNamespace

import pytest

from backend.app.assessment_context_planner import plan_assessment_context
from backend.app.model_provider import ModelProviderError


def test_assessment_context_keeps_source_and_bounds_optional_history():
    provider = SimpleNamespace(context_input_budget_tokens=2000)
    context = {"conceptIds": ["c1"], "concept": "limits", "manifestId": "m1",
               "sources": [{"spanId": f"s{i}", "text": "source " + "x" * 1100} for i in range(4)],
               "evidence": {"detail": "e" * 10000}}
    previous = [{"stem": f"prior {i} " + "p" * 400, "family": "reasoning"} for i in range(10)]

    selected, history = plan_assessment_context(provider, context, previous, {"type": "object"})

    assert selected["sources"]
    assert selected["sources"][0]["spanId"] == "s0"
    assert len(selected["sources"]) < len(context["sources"])
    assert "evidence" not in selected
    assert len(history) < len(previous)


def test_assessment_context_rejects_budget_without_required_source():
    provider = SimpleNamespace(context_input_budget_tokens=800)
    context = {"conceptIds": ["c1"], "concept": "limits",
               "sources": [{"spanId": "s0", "text": "x" * 6000}]}
    with pytest.raises(ModelProviderError, match="Narrow the selected material"):
        plan_assessment_context(provider, context, [], {})
