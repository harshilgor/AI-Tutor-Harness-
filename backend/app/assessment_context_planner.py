"""Budget the source-backed context used by assessment author and checker calls."""
from __future__ import annotations

from .context_engine import ContextBlock, ContextEngine, estimate_tokens
from .model_provider import ModelProviderError


def plan_assessment_context(provider, context: dict, previous: list[dict], schema: dict) -> tuple[dict, list[dict]]:
    """Keep required quiz identity and at least one source; trim optional history first."""
    sources = context.get("sources") or []
    if not sources:
        raise ModelProviderError("Attach readable reference material before generating a quiz. Questions need a source basis.")
    configured = getattr(provider, "context_input_budget_tokens", 12000)
    budget = configured if isinstance(configured, int) and configured > 0 else 12000
    # Reserve the schema, instructions, and a modest repair message before
    # allowing evidence to occupy the prompt. The provider response has its
    # own output budget.
    reserved = estimate_tokens(schema) + 700
    available = max(1, budget - reserved)
    essential = {key: value for key, value in context.items() if key not in {"sources", "evidence", "recentFeedback"}}
    candidates = [ContextBlock("assessment", essential, "assessment_request", 0, True),
                  ContextBlock("source_0", sources[0], "material_span", 1, True)]
    candidates.extend(ContextBlock(f"source_{i}", source, "material_span", 2 + i)
                      for i, source in enumerate(sources[1:], 1))
    if context.get("evidence"):
        candidates.append(ContextBlock("evidence", context["evidence"], "learner_evidence", 30))
    if context.get("recentFeedback"):
        candidates.append(ContextBlock("recentFeedback", context["recentFeedback"], "assessment_feedback", 31))
    for i, item in enumerate(reversed(previous[-20:])):
        candidates.append(ContextBlock(f"prior_{i}", {"stem": item.get("stem"), "family": item.get("family")},
                                       "assessment_history", 40 + i))
    try:
        plan = ContextEngine(input_budget_tokens=available, recent_budget_tokens=0).build_generation_context(
            instructions="Author a source-backed assessment item.", current_user_message=str(essential.get("concept", "assessment")),
            candidates=candidates, turns=[])
    except ValueError as exc:
        raise ModelProviderError("The assessment context exceeds this model's input budget. Narrow the selected material.") from exc
    selected = {block.kind: block.content for block in plan.blocks}
    bounded_context = {**essential,
                       "sources": [selected[f"source_{i}"] for i in range(len(sources)) if f"source_{i}" in selected]}
    for key in ("evidence", "recentFeedback"):
        if key in selected:
            bounded_context[key] = selected[key]
    selected_previous = [selected[f"prior_{i}"] for i in reversed(range(min(len(previous), 20)))
                         if f"prior_{i}" in selected]
    return bounded_context, selected_previous
