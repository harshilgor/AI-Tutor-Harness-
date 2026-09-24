"""Privacy-conscious metadata and fingerprints for planned provider context."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def source_metadata(value: Any) -> tuple[list[str], list[str]]:
    """Extract identifiers and revision markers without copying source text."""
    ids: set[str] = set()
    revisions: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, entry in item.items():
                normalized = key.lower()
                if normalized == "versionid" and isinstance(entry, (str, int)):
                    ids.add(f"{key}:{entry}")
                    revisions.add(f"{key}:{entry}")
                elif normalized.endswith("id") and isinstance(entry, (str, int)):
                    ids.add(f"{key}:{entry}")
                elif "revision" in normalized or normalized in {"version", "versionnumber"}:
                    if isinstance(entry, (str, int, float)):
                        revisions.add(f"{key}:{entry}")
                    else:
                        walk(entry)
                else:
                    walk(entry)
        elif isinstance(item, (list, tuple)):
            for entry in item:
                walk(entry)

    walk(value)
    return sorted(ids), sorted(revisions)


def block_decision(block) -> dict[str, Any]:
    source_ids, revisions = source_metadata(block.content)
    content = json.dumps(block.content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return {
        "kind": block.kind,
        "source": block.source,
        "priority": block.priority,
        "required": block.required,
        "relevanceScore": block.relevance_score,
        "estimatedTokens": block.estimated_tokens,
        "sourceIds": source_ids,
        "revisions": revisions,
        "contentSha256": hashlib.sha256(content).hexdigest(),
    }


def provider_input_fingerprint(provider: str, model: str, payload: Any) -> str:
    """Hash canonical provider/model/payload; never persist payload contents."""
    canonical = json.dumps({"provider": provider, "model": model, "payload": payload},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(canonical).hexdigest()
