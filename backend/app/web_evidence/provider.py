"""Provider-neutral web evidence interface and test double."""

from __future__ import annotations

from typing import Protocol

from .models import PolicyDecision, ProviderError, ProviderOpenResult, ProviderSearchHit, SearchIntent


class WebEvidenceProvider(Protocol):
    provider_name: str

    @property
    def available(self) -> bool: ...

    def search(
        self,
        query: str,
        *,
        intent: SearchIntent,
        decision: PolicyDecision,
        cancel_check=None,
    ) -> list[ProviderSearchHit]: ...

    def open_result(
        self,
        provider_result_ref: str,
        *,
        focus: str | None,
        decision: PolicyDecision,
        cancel_check=None,
    ) -> ProviderOpenResult: ...


class FakeWebEvidenceProvider:
    """Deterministic provider for unit tests. Never contacts the network."""

    provider_name = "fake"

    def __init__(
        self,
        *,
        hits: list[ProviderSearchHit] | None = None,
        open_results: dict[str, ProviderOpenResult] | None = None,
        available: bool = True,
        search_error: Exception | None = None,
        open_error: Exception | None = None,
    ):
        self._available = available
        self.hits = hits or []
        self.open_results = open_results or {}
        self.search_error = search_error
        self.open_error = open_error
        self.search_calls: list[dict] = []
        self.open_calls: list[dict] = []

    @property
    def available(self) -> bool:
        return self._available

    def search(
        self,
        query: str,
        *,
        intent: SearchIntent,
        decision: PolicyDecision,
        cancel_check=None,
    ) -> list[ProviderSearchHit]:
        if cancel_check and cancel_check():
            raise ProviderError("cancelled", "Retrieval was cancelled.")
        self.search_calls.append({"query": query, "intent": intent, "decision": decision})
        if self.search_error:
            raise self.search_error
        limited = self.hits[: decision.max_results]
        if decision.domain_allowlist:
            allowed = set(decision.domain_allowlist)
            limited = [h for h in limited if h.domain in allowed]
        if decision.domain_denylist:
            denied = set(decision.domain_denylist)
            limited = [h for h in limited if h.domain not in denied]
        return [
            hit.model_copy(update={"excerpt": hit.excerpt[: decision.max_chars_per_source]})
            for hit in limited
        ]

    def open_result(
        self,
        provider_result_ref: str,
        *,
        focus: str | None,
        decision: PolicyDecision,
        cancel_check=None,
    ) -> ProviderOpenResult:
        if cancel_check and cancel_check():
            raise ProviderError("cancelled", "Retrieval was cancelled.")
        self.open_calls.append({"ref": provider_result_ref, "focus": focus})
        if self.open_error:
            raise self.open_error
        result = self.open_results.get(provider_result_ref)
        if result is None:
            raise ProviderError("not_found", "Provider result is not available.")
        excerpt = result.excerpt
        if focus:
            excerpt = f"{focus}: {excerpt}"
        return result.model_copy(update={"excerpt": excerpt[: decision.max_chars_per_source]})
