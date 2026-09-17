"""The first reviewed, versioned subject pack.

Packs are deliberately data, not executable extensions.  This keeps their
source and graph contract inspectable and lets a session pin a version.
"""
from __future__ import annotations

from copy import deepcopy
from fastapi import HTTPException

from .models import Concept, Edge, GraphVersion, SourceReference, TopicScope, utc_now


NEURAL_NETWORK_FOUNDATIONS = {
    "id": "neural-network-foundations",
    "version": 1,
    "title": "Neural network foundations",
    "reviewedSources": [
        {"id": "nn-source-goodfellow-ch6", "title": "Deep Learning, Chapter 6: Deep Feedforward Networks", "url": "https://www.deeplearningbook.org/contents/mlp.html", "locator": "Sections 6.1–6.5"},
        {"id": "nn-source-3b1b-backprop", "title": "3Blue1Brown: What is backpropagation really doing?", "url": "https://www.3blue1brown.com/lessons/backpropagation", "locator": "Lesson overview"},
    ],
    "concepts": [
        {"id": "nn-neuron", "title": "Weighted neuron", "summary": "A neuron combines weighted inputs and a bias before applying an activation.", "sourceIds": ["nn-source-goodfellow-ch6"]},
        {"id": "nn-activation", "title": "Activation functions", "summary": "Nonlinear activations let layered networks represent nonlinear relationships.", "sourceIds": ["nn-source-goodfellow-ch6"]},
        {"id": "nn-loss", "title": "Loss and prediction error", "summary": "A loss function measures how a prediction differs from a target.", "sourceIds": ["nn-source-goodfellow-ch6"]},
        {"id": "nn-backprop", "title": "Backpropagation", "summary": "Backpropagation applies the chain rule to calculate how parameters affect loss.", "sourceIds": ["nn-source-goodfellow-ch6", "nn-source-3b1b-backprop"]},
    ],
    "edges": [
        {"id": "nn-neuron-activation", "source": "nn-neuron", "target": "nn-activation", "type": "requires", "justification": "Activation is applied after a neuron's weighted sum.", "sourceIds": ["nn-source-goodfellow-ch6"]},
        {"id": "nn-activation-loss", "source": "nn-activation", "target": "nn-loss", "type": "requires", "justification": "Predictions produced by the network are compared with targets through a loss.", "sourceIds": ["nn-source-goodfellow-ch6"]},
        {"id": "nn-loss-backprop", "source": "nn-loss", "target": "nn-backprop", "type": "requires", "justification": "Backpropagation differentiates loss with respect to parameters.", "sourceIds": ["nn-source-goodfellow-ch6"]},
    ],
    "assessmentBlueprints": [
        {"id": "nn-backprop-chain-rule", "conceptId": "nn-backprop", "skill": "explain_chain_rule", "sourceIds": ["nn-source-goodfellow-ch6"], "prompt": "Explain why a local derivative participates in a parameter gradient."},
        {"id": "nn-loss-direction", "conceptId": "nn-loss", "skill": "reason_about_loss", "sourceIds": ["nn-source-goodfellow-ch6"], "prompt": "Compare a prediction and target, then reason about the loss direction."},
    ],
    "evaluationFixtures": [
        {"id": "nn-fixture-backprop", "blueprintId": "nn-backprop-chain-rule", "expectedConceptId": "nn-backprop", "prompt": "Why does a layer receive a downstream error signal?"},
    ],
}


def packs() -> list[dict]:
    return [deepcopy(NEURAL_NETWORK_FOUNDATIONS)]


def get_pack(pack_id: str, version: int | None = None) -> dict:
    pack = next((item for item in packs() if item["id"] == pack_id), None)
    if pack is None or (version is not None and pack["version"] != version):
        raise HTTPException(status_code=404, detail={"code": "domain_pack_not_found", "message": "That domain pack version is not available."})
    validate_pack(pack)
    return pack


def validate_pack(pack: dict) -> None:
    source_ids = {source["id"] for source in pack.get("reviewedSources", [])}
    concept_ids = {concept["id"] for concept in pack.get("concepts", [])}
    if not source_ids or not concept_ids:
        raise ValueError("A domain pack requires reviewed sources and concepts.")
    for concept in pack["concepts"]:
        if not set(concept.get("sourceIds", [])).issubset(source_ids):
            raise ValueError(f"Concept {concept['id']} references an unknown source.")
    for edge in pack.get("edges", []):
        if edge.get("source") not in concept_ids or edge.get("target") not in concept_ids:
            raise ValueError(f"Edge {edge.get('id', '<unknown>')} references an unknown concept.")
        if not set(edge.get("sourceIds", [])).issubset(source_ids):
            raise ValueError(f"Edge {edge.get('id', '<unknown>')} references an unknown source.")
    blueprint_ids = {item["id"] for item in pack.get("assessmentBlueprints", [])}
    for blueprint in pack.get("assessmentBlueprints", []):
        if blueprint.get("conceptId") not in concept_ids:
            raise ValueError(f"Blueprint {blueprint['id']} references an unknown concept.")
        if not blueprint.get("skill"):
            raise ValueError(f"Blueprint {blueprint['id']} requires a skill.")
        if not set(blueprint.get("sourceIds", [])).issubset(source_ids):
            raise ValueError(f"Blueprint {blueprint['id']} references an unknown source.")
    for fixture in pack.get("evaluationFixtures", []):
        if fixture.get("blueprintId") not in blueprint_ids or fixture.get("expectedConceptId") not in concept_ids:
            raise ValueError(f"Evaluation fixture {fixture.get('id', '<unknown>')} has an invalid blueprint or concept.")


def graph_for_pack(pack: dict) -> GraphVersion:
    validate_pack(pack)
    graph_id = f"domain-pack:{pack['id']}:{pack['version']}"
    return GraphVersion(
        id=graph_id, scope_id=f"domain-pack:{pack['id']}", title=pack["title"],
        description="A reviewed, bounded first-party curriculum pack.", version=pack["version"],
        publication_state="published", trust_summary="Concepts and relationships are linked to the reviewed pack sources; teaching and assessment still disclose their individual source coverage.",
        concepts=[Concept(id=item["id"], title=item["title"], label="Foundation", summary=item["summary"], objective=f"Understand {item['title']}", source_ids=item["sourceIds"], support_status="supported") for item in pack["concepts"]],
        edges=[Edge(id=item["id"], source=item["source"], target=item["target"], type=item["type"], justification=item["justification"], support_status="supported") for item in pack["edges"]],
        sources=[SourceReference(id=item["id"], title=item["title"], url=item.get("url"), locator=item.get("locator"), support_status="supported") for item in pack["reviewedSources"]],
        generated_by="first_party_domain_pack", created_at=utc_now(),
    )
