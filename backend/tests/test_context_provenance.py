"""Traceability metadata must identify decisions without retaining prompts."""
from backend.app.context_engine import ContextBlock, ContextEngine
from backend.app.context_provenance import block_decision, provider_input_fingerprint


def test_block_decision_records_source_revisions_relevance_and_content_hash():
    block = ContextBlock(
        "automaticNotes",
        [{"noteId": "note-7", "versionId": "version-3", "revision": 4, "relevanceScore": 0.82, "text": "private note text"}],
        "learner_note_search", 6, relevance_score=0.82,
    )
    decision = block_decision(block)
    assert "noteId:note-7" in decision["sourceIds"]
    assert "revision:4" in decision["revisions"]
    assert "versionId:version-3" in decision["revisions"]
    assert decision["relevanceScore"] == 0.82
    assert decision["contentSha256"]
    assert "private note text" not in str(decision)


def test_provider_fingerprint_tracks_canonical_actual_payload_and_model():
    payload = {"messages": [{"role": "user", "content": "question"}]}
    initial = provider_input_fingerprint("openrouter", "model-a", payload)
    assert initial == provider_input_fingerprint("openrouter", "model-a", {"messages": list(payload["messages"])})
    assert initial != provider_input_fingerprint("openrouter", "model-a", {"messages": [{"role": "user", "content": "changed"}]})
    assert initial != provider_input_fingerprint("openrouter", "model-b", payload)


def test_budget_omissions_include_source_ids_and_concrete_reason():
    context = ContextEngine(500, 100).build_generation_context(
        instructions="Teach.", current_user_message="Use the relevant source.", turns=[],
        candidates=[ContextBlock("sources", [
            {"spanId": "too-large", "versionId": "version-3", "revision": 9, "text": "x" * 2000},
        ], "course_material", 5, relevance_score=0.77)],
    )
    omission = context.omission_reasons[0]
    assert omission["kind"] == "sources"
    assert omission["reason"] == "some_items_exceed_remaining_budget" or omission["reason"] == "block_exceeds_remaining_budget"
    assert "spanId:too-large" in omission["omittedSourceIds"]
    assert omission["relevanceScore"] == 0.77
