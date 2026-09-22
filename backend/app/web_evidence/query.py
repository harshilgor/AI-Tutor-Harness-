"""Minimal search-query construction with privacy scrubbing."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_INTERNAL_ID = re.compile(r"\b(?:learner|user|session|tenant|course|note|span|evidence)_[A-Za-z0-9]+\b", re.I)
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_LONG_HEX = re.compile(r"\b[0-9a-f]{20,}\b", re.I)
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


def scrub_sensitive(text: str) -> str:
    cleaned = _EMAIL.sub("[redacted-email]", text)
    cleaned = _PHONE.sub("[redacted-phone]", cleaned)
    cleaned = _INTERNAL_ID.sub("[redacted-id]", cleaned)
    cleaned = _UUID.sub("[redacted-id]", cleaned)
    cleaned = _LONG_HEX.sub("[redacted-id]", cleaned)
    return " ".join(cleaned.split())


def build_public_query(
    *,
    model_query: str,
    topic: str | None = None,
    learning_objective: str | None = None,
    max_length: int = 280,
) -> str:
    """Build a minimized public web query. Does not include learner identity."""
    parts = [scrub_sensitive(model_query)]
    if topic:
        parts.append(scrub_sensitive(topic))
    # Prefer the model query; only append a short objective fragment when query is thin.
    if learning_objective and len(parts[0]) < 40:
        parts.append(scrub_sensitive(learning_objective)[:80])
    query = " ".join(p for p in parts if p).strip()
    if len(query) > max_length:
        query = query[: max_length - 1].rsplit(" ", 1)[0] + "…"
    return query
