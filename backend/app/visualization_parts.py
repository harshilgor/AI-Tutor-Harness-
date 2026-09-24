"""Place visual message parts between Markdown paragraphs without touching code fences."""
from __future__ import annotations

from .visualization_models import VisualizationSpec


def paragraphs(markdown: str) -> list[str]:
    groups: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("'''") or line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not line.strip() and not in_fence and current:
            groups.append(current)
            current = []
        else:
            current.append(line)
    if current:
        groups.append(current)
    return ["\n".join(lines).strip() for lines in groups if any(line.strip() for line in lines)]


def make_visual_parts(body: str, visuals: list[VisualizationSpec]) -> list[dict]:
    if not visuals:
        return []
    chunks = paragraphs(body) or [body]
    parts: list[dict] = []
    for index, chunk in enumerate(chunks):
        parts.append({"kind": "text", "text": chunk})
        for visual in visuals:
            if min(visual.after_paragraph, len(chunks) - 1) == index:
                parts.append({"kind": "visualization", "visualizationId": visual.id})
    return parts
