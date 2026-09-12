"""Graph generation boundary.

The baseline deliberately creates a bounded instructional scaffold from the
topic string only. It does not claim domain facts or source support. A model
and retrieval provider can replace this implementation behind the same
interface once credentials and source policy are selected.
"""

from __future__ import annotations

from uuid import uuid4

from .models import Concept, Edge, GraphVersion, SourceReference, TopicScope, utc_now


class GraphGenerator:
    provider_name = "deterministic_baseline"

    def generate(self, scope: TopicScope) -> GraphVersion:
        topic = scope.topic
        objective = scope.objective
        names = [
            ("orientation", f"What is {topic}?", "A working definition and the question this topic helps us answer."),
            ("parts", f"The parts of {topic}", "Identify the main pieces that make up the topic and how to name them."),
            ("relationships", f"How {topic} connects", "Trace relationships between the parts instead of memorizing isolated labels."),
            ("mechanism", f"How {topic} behaves", "Use a simple mechanism to explain what changes and why."),
            ("example", f"An example of {topic}", "Apply the idea to one concrete situation and state the assumptions."),
            ("boundaries", f"Limits of {topic}", "Notice where the model stops applying and what remains uncertain."),
            ("transfer", f"Use {topic} independently", "Explain or apply the idea in a new setting without following a worked template."),
        ]
        concepts = [
            Concept(
                id=f"concept_{slug}_{uuid4().hex[:8]}",
                title=title,
                label="Start here" if index == 0 else ["Foundations", "Structure", "Mechanism", "Example", "Boundaries", "Transfer"][index - 1],
                summary=summary,
                objective=objective,
            )
            for index, (slug, title, summary) in enumerate(names)
        ]
        edges: list[Edge] = []
        # Keep the baseline graph acyclic and easy to inspect. These are
        # proposed teaching connections, not verified domain prerequisites.
        for source, target in zip(concepts, concepts[1:]):
            edges.append(
                Edge(
                    id=f"edge_{uuid4().hex[:8]}",
                    source=source.id,
                    target=target.id,
                    type="related_to" if target is concepts[-1] else "requires",
                    justification="Baseline instructional sequence; review before treating as a strict prerequisite.",
                    support_status="inferred",
                )
            )
        return GraphVersion(
            id=f"graph_{uuid4().hex}",
            scope_id=scope.id,
            title=topic,
            description=f"A bounded first pass through {topic}, organized around a learnable path.",
            publication_state="limited_unverified",
            trust_summary="Generated without a model or retrieved sources. Concepts and relationships are instructional proposals pending source review.",
            concepts=concepts,
            edges=edges,
            sources=[
                SourceReference(
                    id=f"source_{uuid4().hex[:8]}",
                    title="No source pack configured",
                    support_status="unverified",
                )
            ],
            generated_by=self.provider_name,
            created_at=utc_now(),
        )

