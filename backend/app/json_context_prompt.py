"""Shared bounded context assembly for JSON calls."""
from __future__ import annotations

import json
from typing import Any

from .context_engine import ContextBlock, ContextEngine, GenerationContext
from .model_provider import ModelProviderError


def bounded_json_prompt(provider: Any, instructions: str, payload: dict[str, Any], *,
                        required: set[str], reserve_tokens: int = 0) -> str | GenerationContext:
    configured = getattr(provider, "context_input_budget_tokens", 12000)
    budget = configured if isinstance(configured, int) and configured > 0 else 12000
    budget = max(1, budget - reserve_tokens)
    candidates = [ContextBlock(key, value, key, index, key in required)
                  for index, (key, value) in enumerate(payload.items())]
    try:
        plan = ContextEngine(input_budget_tokens=budget, recent_budget_tokens=0).build_generation_context(
            instructions=instructions,
            current_user_message="Generate the requested JSON response.",
            candidates=candidates,
            turns=[],
        )
    except ValueError as exc:
        raise ModelProviderError("The selected context exceeds this model's input budget. Narrow the source or request.") from exc
    if getattr(provider, "supports_generation_context", False):
        return plan
    selected = {block.kind: block.content for block in plan.blocks}
    return instructions + "\n" + json.dumps(selected, ensure_ascii=False)
