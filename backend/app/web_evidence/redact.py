"""Redaction helpers — never leak keys or sensitive payloads."""

from __future__ import annotations

import re
from typing import Any

_SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|bearer|password|secret|token)\s*[:=]\s*['\"]?([^\s'\"]+)"
)
_LONG_TOKEN = re.compile(r"\b(?:sk|exa)[-_][A-Za-z0-9]{8,}\b")


def redact_text(value: str, *, api_key: str | None = None) -> str:
    text = value or ""
    if api_key:
        text = text.replace(api_key, "[redacted-key]")
    text = _SECRET.sub(r"\1=[redacted]", text)
    text = _LONG_TOKEN.sub("[redacted-token]", text)
    return text


def redact_mapping(data: dict[str, Any], *, api_key: str | None = None) -> dict[str, Any]:
    blocked = {
        "api_key", "apiKey", "authorization", "headers", "excerpt", "text",
        "raw", "raw_meta", "provider_result_ref", "providerResultRef",
    }
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key in blocked:
            out[key] = "[redacted]"
            continue
        if isinstance(value, str):
            out[key] = redact_text(value, api_key=api_key)
        elif isinstance(value, dict):
            out[key] = redact_mapping(value, api_key=api_key)
        else:
            out[key] = value
    return out


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"
