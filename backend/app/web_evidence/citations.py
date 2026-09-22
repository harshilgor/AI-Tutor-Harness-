"""Citation mapping and validation against response-bundle aliases only."""

from __future__ import annotations

import re

from .lifecycle import EvidenceOutcome
from .models import EvidenceBundle, EvidencePacket


_CITATION_REF = re.compile(r"\[(?:source|web|cite|material):([WwMm]\d{1,2})\]", re.I)
_INVENTED_URL = re.compile(r"https?://[^\s\]]+", re.I)
_FALSE_RETRIEVAL = re.compile(
    r"(?i)\b(i (found|retrieved|searched|looked up)|according to my (search|sources))\b"
)


class CitationValidation:
    def __init__(
        self,
        *,
        ok: bool,
        cited_aliases: list[str],
        unknown_aliases: list[str],
        invented_urls: list[str],
        false_retrieval_claim: bool,
        web_claims_without_citation: bool,
    ):
        self.ok = ok
        self.cited_aliases = cited_aliases
        self.unknown_aliases = unknown_aliases
        self.invented_urls = invented_urls
        self.false_retrieval_claim = false_retrieval_claim
        self.web_claims_without_citation = web_claims_without_citation


class CitationMapper:
    def __init__(self, bundle: EvidenceBundle):
        self.bundle = bundle
        self.by_alias = {p.alias.upper(): p for p in bundle.packets}

    def learner_citations(self, aliases: list[str] | None = None) -> list[dict]:
        ids = aliases or [p.alias for p in self.bundle.packets]
        out = []
        for alias in ids:
            packet = self.by_alias.get(alias.upper())
            if packet is None:
                continue
            out.append(self._render(packet))
        return out

    def _render(self, packet: EvidencePacket) -> dict:
        # Always render from server-stored packet fields — never model text.
        return {
            "alias": packet.alias,
            "title": packet.title,
            "domain": packet.domain,
            "url": packet.canonical_url,
            "publishedDate": packet.published_date,
            "sourceKind": packet.source_kind.value,
            "classification": packet.source_classification.value,
            "trustLabel": packet.trust_label.value,
        }

    def validate_response_text(self, text: str, *, expect_web_citations: bool = False) -> CitationValidation:
        body = text or ""
        cited = [m.upper() if m[0].lower() in "wm" else m for m in _CITATION_REF.findall(body)]
        cited = [c[0].upper() + c[1:] for c in cited]
        unknown = [alias for alias in cited if alias.upper() not in self.by_alias]
        invented = []
        allowed_urls = {p.canonical_url for p in self.bundle.packets if p.canonical_url}
        for match in _INVENTED_URL.findall(body):
            if match.rstrip(").,]") not in allowed_urls:
                invented.append(match)
        false_claim = bool(_FALSE_RETRIEVAL.search(body)) and not self.bundle.retrieval_occurred
        web_aliases = {a for a, p in self.by_alias.items() if p.source_kind.value == "web"}
        cited_web = [a for a in cited if a.upper() in web_aliases]
        missing = bool(expect_web_citations and web_aliases and not cited_web)
        if self.bundle.evidence_outcome == EvidenceOutcome.no_reliable_evidence and cited_web:
            missing = True
        ok = not unknown and not invented and not false_claim and not missing
        return CitationValidation(
            ok=ok,
            cited_aliases=cited,
            unknown_aliases=unknown,
            invented_urls=invented,
            false_retrieval_claim=false_claim,
            web_claims_without_citation=missing,
        )
