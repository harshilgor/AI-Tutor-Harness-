import json
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.model_provider import OpenRouterLessonProvider
from backend.app.review.question_service import generate_question


class _Serializable:
    def __init__(self, value):
        self.value = value

    def model_dump(self, **kwargs):
        return self.value


def test_typed_lesson_prompt_retains_branch_anchor_and_bounds_notes():
    provider = OpenRouterLessonProvider("unused", "model", None, None)
    provider.context_input_budget_tokens = 1500
    context = SimpleNamespace(
        request_message="Explain this branch", branch_id="b1", parent_branch_id="b0",
        anchor={"selectedText": "a local passage"},
        teaching_profile=_Serializable({"gear": "guided"}),
        learner_evidence=_Serializable({"long": "e" * 15000}),
    )
    graph = SimpleNamespace(title="Topic")
    concept = SimpleNamespace(title="Concept")
    plan = SimpleNamespace(strategy=SimpleNamespace(value="direct"), representation_sequence=["mechanism"])
    intent = SimpleNamespace(value="teach")

    with patch.object(provider, "_complete", return_value=[]) as complete:
        provider.generate(graph=graph, concept=concept, context=context, plan=plan, intent=intent,
                          note_context=[{"body": "n" * 15000}])

    prompt = complete.call_args.args[0]
    selected = {block.kind: block.content for block in prompt.blocks}
    assert selected["branch"]["anchor"]["selectedText"] == "a local passage"
    assert prompt.current_user_message == "Explain this branch"
    assert "learnerEvidence" not in selected
    assert "learnerNotes" not in selected
    assert '{"blocks"' in prompt.instructions


def test_review_question_prompt_bounds_history_and_source():
    class Provider:
        context_input_budget_tokens = 1000

        def complete_json(self, prompt, max_tokens):
            self.payload = json.loads(prompt.rsplit("\n", 1)[1])
            return {"question_type": "explain", "prompt": "Explain the core relationship.", "expected_answer": "A clear reason."}

    provider = Provider()
    result = generate_question(provider, concept_title="Limits", concept_summary="A boundary",
                               source_excerpt="s" * 10000, recent_questions=["old " + "q" * 500] * 5)
    assert result.question_type == "explain"
    assert provider.payload["concept"]["title"] == "Limits"
    assert len(provider.payload["source_excerpt"]) < 10000
    assert len(provider.payload["recent_questions"]) < 5
