"""Deterministic learning-kernel policy used until a model provider is added.

The kernel still performs the important orchestration steps: intent selection,
bounded graph-context assembly, teaching-profile resolution, and a structured
lesson artifact.  Its output is explicitly qualified so it cannot be mistaken
for source-verified domain teaching.
"""

from __future__ import annotations

from uuid import uuid4

from .models import Concept, GraphVersion
from .session_models import (
    ConceptTrust,
    LessonArtifact,
    LessonBlock,
    TeachingActionInput,
    TeachingGear,
    TeachingIntent,
)


def classify_intent(request: TeachingActionInput) -> TeachingIntent:
    """Return the typed intent, using the message only for free-form prompts."""

    if request.intent != TeachingIntent.teach:
        return request.intent
    message = (request.message or "").lower()
    if any(token in message for token in ("simpler", "simple", "plain language", "easier")):
        return TeachingIntent.simplify
    if any(token in message for token in ("example", "apply", "application")):
        return TeachingIntent.example
    if any(token in message for token in ("why", "how does", "how do")):
        return TeachingIntent.why
    if any(token in message for token in ("visual", "diagram", "draw")):
        return TeachingIntent.visualize
    if any(token in message for token in ("test me", "check me", "quiz", "understanding")):
        return TeachingIntent.check_understanding
    if any(token in message for token in ("continue", "resume", "where i left")):
        return TeachingIntent.resume
    return TeachingIntent.teach


def resolve_concept(graph: GraphVersion, requested_id: str | None) -> Concept:
    if requested_id:
        for concept in graph.concepts:
            if concept.id == requested_id:
                return concept
    return graph.concepts[0]


def _trust(concept: Concept) -> ConceptTrust:
    # Graph concepts currently use the original graph contract. Preserve its
    # provenance semantics when projecting into the lesson contract.
    status = {
        "supported": "supported",
        "partial": "partially_supported",
        "unverified": "insufficient",
    }.get(concept.support_status, "insufficient")
    return ConceptTrust(status=status, source_ids=list(concept.source_ids))


def build_lesson(graph: GraphVersion, concept: Concept, request: TeachingActionInput, session_id: str, intent: TeachingIntent, graph_revision: int, action_id: str) -> LessonArtifact:
    gear = request.gear or TeachingGear.guided
    trust = _trust(concept)
    label = "This is a working scaffold"
    core = (
        f"{concept.summary} Start by naming the idea, then connect it to the question you are trying to answer. "
        "The map treats this as a proposed learning connection, so domain claims still need source review."
    )
    if intent == TeachingIntent.simplify:
        core = f"In everyday terms: {concept.summary} Think of it as a useful handle for organizing the topic before adding detail."
    elif intent == TeachingIntent.why:
        core = f"The reason to study {concept.title.lower()} is that relationships explain more than isolated labels. {concept.summary}"
    elif intent == TeachingIntent.example:
        core = f"Try this small thought experiment: choose one familiar situation involving {graph.title}. Identify the parts, then ask which relationship the situation makes visible."
    elif intent == TeachingIntent.visualize:
        core = f"Picture {concept.title.lower()} as a node connected to the question, its parts, its mechanism, and one boundary. Follow one connection at a time instead of reading the whole map at once."
    elif intent == TeachingIntent.resume:
        core = f"Welcome back. We were working with {concept.title.lower()}. {concept.summary} Start by restating the idea in your own words, then we can continue."
    elif intent == TeachingIntent.check_understanding:
        core = f"Before moving on, explain in one sentence what role {concept.title.lower()} plays in {graph.title}. Your response is the useful evidence; opening this lesson does not change mastery."

    blocks = [
        LessonBlock(
            id=f"block_{uuid4().hex[:10]}",
            kind="explanation",
            heading="Start with the idea",
            body=core,
            concept_ids=[concept.id],
            source_ids=list(concept.source_ids),
            trust=trust,
            order=0,
        )
    ]
    if gear in (TeachingGear.guided, TeachingGear.deep):
        blocks.append(
            LessonBlock(
                id=f"block_{uuid4().hex[:10]}",
                kind="example",
                heading="A concrete handle",
                body=f"Use {graph.title} as the setting. Point to one part, one interaction, and one observable consequence. If you cannot name the interaction, that is the next useful question.",
                concept_ids=[concept.id],
                source_ids=list(concept.source_ids),
                trust=trust,
                order=1,
            )
        )
    if gear == TeachingGear.deep:
        blocks.append(
            LessonBlock(
                id=f"block_{uuid4().hex[:10]}",
                kind="analogy",
                heading="Go one level deeper",
                body=f"Separate the boundary of {graph.title} from the behavior inside it. Then ask which assumption would have to change for this explanation to stop being useful. That boundary check prevents a teaching shortcut from becoming a universal rule.",
                concept_ids=[concept.id],
                source_ids=list(concept.source_ids),
                trust=trust,
                order=2,
            )
        )
    blocks.extend(
        [
            LessonBlock(
                id=f"block_{uuid4().hex[:10]}",
                kind="reflection",
                heading="Your turn",
                body=f"In your own words, what is {concept.title.lower()} helping you notice? Keep the answer short; the goal is to expose the next gap, not to sound polished.",
                concept_ids=[concept.id],
                source_ids=list(concept.source_ids),
                trust=trust,
                order=len(blocks),
            ),
            LessonBlock(
                id=f"block_{uuid4().hex[:10]}",
                kind="source_note",
                heading=label,
                body="This response came from the deterministic local provider. It is suitable for exercising the learning flow, but it is not a source-verified answer and does not update mastery.",
                concept_ids=[concept.id],
                source_ids=list(concept.source_ids),
                trust=trust,
                order=len(blocks) + 1,
                metadata={"provider": "deterministic_baseline", "qualified": True},
            ),
        ]
    )
    return LessonArtifact(
        id=f"lesson_{uuid4().hex}",
        session_id=session_id,
        concept_id=concept.id,
        graph_revision=graph_revision,
        gear=gear,
        title=concept.title,
        blocks=blocks,
        next_action="check_understanding" if intent != TeachingIntent.check_understanding else "continue",
        status="qualified",
        verification_run_id=action_id,
        generated_by="deterministic_baseline",
    )

