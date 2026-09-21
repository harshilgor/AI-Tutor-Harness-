"""Shared durable generation orchestrator and bounded live event buffer."""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol

from .generation_models import GenerationEvent, GenerationRequest
from .generation_store import GenerationStore, TERMINAL
from .journey_service import JourneyService
from .model_provider import ModelProviderError, usage_metrics
from .streaming_lesson import ProgressiveLessonParser

ERRORS = {"VALIDATION_FAILED", "CONTEXT_FAILED", "PROVIDER_TIMEOUT", "PROVIDER_ERROR", "VISION_UNSUPPORTED", "STREAM_INTERRUPTED", "REPLAY_EXPIRED", "CANCELLED", "PERSISTENCE_FAILED", "REVISION_CONFLICT"}


def error_code(exc: Exception) -> str:
    text = str(exc)
    if text in ERRORS:
        return text
    if "revision" in text.lower():
        return "REVISION_CONFLICT"
    if isinstance(exc, ModelProviderError):
        return "PROVIDER_ERROR"
    return "CONTEXT_FAILED"


@dataclass
class _Channel:
    events: deque[GenerationEvent] = field(default_factory=lambda: deque(maxlen=int(os.getenv("GENERATION_STREAM_REPLAY_EVENT_LIMIT", "800"))))
    sequence: int = 0
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)


class ReplayEventStore(Protocol):
    async def append(self, generation_id: str, event_type: str, data: dict | None = None) -> GenerationEvent: ...
    def get_after_sequence(self, generation_id: str, after: int) -> list[GenerationEvent]: ...
    def subscribe(self, generation_id: str, after: int, terminal: bool) -> AsyncIterator[GenerationEvent]: ...
    def expire(self, generation_id: str) -> None: ...
    def has_channel(self, generation_id: str) -> bool: ...


class InMemoryReplayEventStore:
    """In-process replay implementation; replaceable by a shared deployment store."""
    def __init__(self):
        self.channels: dict[str, _Channel] = {}

    def channel(self, generation_id: str) -> _Channel:
        return self.channels.setdefault(generation_id, _Channel())

    async def append(self, generation_id: str, event_type: str, data: dict | None = None) -> GenerationEvent:
        channel = self.channel(generation_id)
        async with channel.condition:
            channel.sequence += 1
            event = GenerationEvent(generation_id=generation_id, sequence=channel.sequence, type=event_type, data=data or {})
            channel.events.append(event)
            channel.condition.notify_all()
            return event

    def get_after_sequence(self, generation_id: str, after: int) -> list[GenerationEvent]:
        channel = self.channels.get(generation_id)
        return [event for event in channel.events if event.sequence > after] if channel else []

    def has_channel(self, generation_id: str) -> bool:
        return generation_id in self.channels

    def expire(self, generation_id: str) -> None:
        self.channels.pop(generation_id, None)

    async def subscribe(self, generation_id: str, after: int, terminal: bool) -> AsyncIterator[GenerationEvent]:
        channel = self.channel(generation_id)
        while True:
            async with channel.condition:
                replay = [event for event in channel.events if event.sequence > after]
                if replay:
                    pass
                elif terminal:
                    return
                else:
                    try:
                        await asyncio.wait_for(channel.condition.wait(), timeout=15)
                    except asyncio.TimeoutError:
                        yield GenerationEvent(generation_id=generation_id, sequence=after, type="generation.context_ready", data={"heartbeat": True})
                    continue
            for event in replay:
                after = event.sequence
                yield event
                if event.type in {"generation.completed", "generation.cancelled", "generation.error"}:
                    return

    publish = append
    observe = subscribe


EventBuffer = InMemoryReplayEventStore


class GenerationManager:
    def __init__(self, store, provider):
        self.store = store
        self.provider = provider
        self.records = GenerationStore(store)
        self.buffer: ReplayEventStore = InMemoryReplayEventStore()
        self.tasks: dict[str, asyncio.Task] = {}
        self.observers: dict[str, int] = {}
        self.disconnect_handles: dict[str, asyncio.TimerHandle] = {}
        self.disconnect_grace_seconds = float(os.getenv("GENERATION_STREAM_DISCONNECT_GRACE_SECONDS", "30"))
        self.flush_characters = int(os.getenv("GENERATION_STREAM_FLUSH_CHARACTERS", "120"))
        self.flush_seconds = int(os.getenv("GENERATION_STREAM_FLUSH_MS", "80")) / 1000

    def create(self, owner: str, session_id: str, request: GenerationRequest, key: str) -> dict:
        if not self.provider:
            raise ModelProviderError("Connect a model provider before starting a generation.")
        record = self.records.create(owner, session_id, request.model_dump(mode="json", by_alias=True), key,
            getattr(self.provider, "provider_name", "unknown"), getattr(self.provider, "model", "unknown"))
        if record["status"] == "queued" and record["id"] not in self.tasks:
            self.tasks[record["id"]] = asyncio.create_task(self._run(record["id"], owner, request), name=record["id"])
        return record

    async def _run(self, generation_id: str, owner: str, request: GenerationRequest) -> None:
        sequence = 0
        started_at = time.time()
        try:
            self.records.transition(generation_id, "preparing")
            self.records.update_metrics(generation_id, {"startedAt": started_at, "queueSeconds": max(0, started_at - self.records.get(owner, generation_id)["createdAt"])})
            await self.buffer.append(generation_id, "generation.started", {"mode": request.mode, "gear": request.gear.value})
            prepared = await asyncio.to_thread(JourneyService(self.store, self.provider).prepare_stream, owner, request_session_id := self.records.get(owner, generation_id)["session"], request)
            context_ready_at = time.time()
            self.records.update_metrics(generation_id, {"contextReadyAt": context_ready_at, "contextBuildSeconds": context_ready_at - started_at})
            await self.buffer.append(generation_id, "generation.context_ready", {"sourceCount": len(prepared["sources"]), "actionId": prepared["actionId"]})
            for source in prepared["sources"]:
                await self.buffer.append(generation_id, "source.added", {"spanId": source.get("spanId"), "title": source.get("title")})
            if self.records.cancelled(generation_id):
                await self._cancel(generation_id)
                return
            self.records.transition(generation_id, "streaming")
            parser = ProgressiveLessonParser(generation_id, prepared["title"])
            chunks: list[str] = []
            first_delta_at = None
            provider_started_at = time.time()
            self.records.update_metrics(generation_id, {"providerStartedAt": provider_started_at})
            provider_stream = self.provider.stream_text(prepared["prompt"], 3500, images=prepared.get("images")) if prepared.get("images") else self.provider.stream_text(prepared["prompt"], 3500)
            async for delta in provider_stream:
                if self.records.cancelled(generation_id):
                    await self._cancel(generation_id)
                    return
                chunks.append(delta)
                if first_delta_at is None:
                    first_delta_at = time.time()
                    self.records.update_metrics(generation_id, {"firstDeltaAt": first_delta_at, "providerTtftSeconds": first_delta_at - provider_started_at, "applicationTtftSeconds": first_delta_at - started_at})
                for operation in parser.feed(delta):
                    event = await self._publish_lesson_operation(generation_id, operation)
                    sequence = event.sequence
            for operation in parser.finish():
                event = await self._publish_lesson_operation(generation_id, operation)
                sequence = event.sequence
            body = "".join(chunks).strip()
            if not body:
                raise ModelProviderError("PROVIDER_ERROR")
            self.records.transition(generation_id, "finalizing", sequence=sequence)
            with self.store.transaction() as connection:
                artifact, journey = JourneyService(self.store, self.provider).commit_stream(connection, owner, prepared, request, body)
                result = {"lessonId": artifact.id, "revision": journey["revision"] + 1, "sessionId": journey["sessionId"]}
                completed_at = time.time(); elapsed = max(completed_at - (first_delta_at or provider_started_at), .001)
                exact_usage = getattr(self.provider, "last_usage", None)
                provider_label = str(getattr(self.provider, "provider_name", "unknown") or "unknown").split("/")[0].lower()
                if provider_label not in {"openrouter", "openai"}:
                    provider_label = "openrouter" if not bool(getattr(self.provider, "is_openai", False)) else "openai"
                final_metrics: dict = {"completedAt": completed_at, "completionSeconds": completed_at - started_at,
                    "outputCharacters": len(body), "estimatedOutputTokens": max(1, len(body) // 4), "estimatedTokensPerSecond": (len(body) / 4) / elapsed}
                exact_fragment = usage_metrics(exact_usage, provider=provider_label) if exact_usage is not None else {}
                if exact_fragment:
                    final_metrics.update(exact_fragment)
                else:
                    final_metrics["usageSource"] = "estimated"
                    final_metrics["usageProvider"] = provider_label
                self.records.update_metrics(generation_id, final_metrics, connection)
                self.records.transition(generation_id, "completed", sequence=sequence, result=result, connection=connection)
            usage_event: dict = {"result": result}
            try:
                completed_record = self.records.get(owner, generation_id)
                completed_metrics = completed_record.get("metrics") or {}
                usage_event["usage"] = {
                    "totalTokens": completed_metrics.get("totalTokens", completed_metrics.get("estimatedOutputTokens", 0)),
                    "promptTokens": completed_metrics.get("promptTokens"),
                    "completionTokens": completed_metrics.get("completionTokens"),
                    "usageSource": completed_metrics.get("usageSource", "estimated"),
                    "provider": completed_record.get("provider"),
                    "model": completed_record.get("model"),
                }
            except Exception:
                pass
            await self.buffer.append(generation_id, "generation.completed", usage_event)
        except asyncio.CancelledError:
            self.records.update_metrics(generation_id, {"cancelled": True, "completedAt": time.time()})
            await self._cancel(generation_id)
            raise
        except Exception as exc:
            code = error_code(exc)
            record = self.records.get(owner, generation_id)
            if record["status"] not in TERMINAL:
                self.records.update_metrics(generation_id, {"errorCode": code, "completedAt": time.time()})
                self.records.transition(generation_id, "failed", error_code=code, sequence=sequence)
                await self.buffer.append(generation_id, "generation.error", {"code": code, "message": "The generation could not be completed. Please try again."})
        finally:
            self.tasks.pop(generation_id, None)

    async def _publish_lesson_operation(self, generation_id, operation):
        if operation.action == "start":
            return await self.buffer.append(generation_id, "lesson.block_started", {"block": {"id": operation.block_id, "kind": operation.kind, "heading": operation.heading}})
        if operation.action == "complete":
            return await self.buffer.append(generation_id, "lesson.block_completed", {"blockId": operation.block_id})
        return await self.buffer.append(generation_id, "text.delta", {"blockId": operation.block_id, "text": operation.text})

    async def _cancel(self, generation_id: str) -> None:
        # Cancellation is set durably before this method; do not publish a terminal
        # event until the provider iterator has been closed by the caller.
        try:
            self.records.transition(generation_id, "cancelled", error_code="CANCELLED")
        except RuntimeError:
            return
        await self.buffer.append(generation_id, "generation.cancelled", {"code": "CANCELLED"})

    def cancel(self, owner: str, generation_id: str) -> dict:
        record = self.records.request_cancel(owner, generation_id)
        task = self.tasks.get(generation_id)
        if task and record["status"] == "cancel_requested":
            # Cancelling the task closes the async provider iterator/context at
            # once. The task emits the terminal event after the connection ends.
            task.cancel()
        return record

    def _attach(self, generation_id: str) -> None:
        self.observers[generation_id] = self.observers.get(generation_id, 0) + 1
        handle = self.disconnect_handles.pop(generation_id, None)
        if handle:
            handle.cancel()

    def _detach(self, owner: str, generation_id: str) -> None:
        count = max(0, self.observers.get(generation_id, 1) - 1)
        self.observers[generation_id] = count
        if count or generation_id not in self.tasks:
            return
        loop = asyncio.get_running_loop()
        self.disconnect_handles[generation_id] = loop.call_later(
            self.disconnect_grace_seconds,
            lambda: asyncio.create_task(self._cancel_after_disconnect(owner, generation_id)),
        )

    async def _cancel_after_disconnect(self, owner: str, generation_id: str) -> None:
        if self.observers.get(generation_id, 0) == 0 and generation_id in self.tasks:
            self.cancel(owner, generation_id)

    async def events(self, owner: str, generation_id: str, after: int) -> AsyncIterator[GenerationEvent]:
        record = self.records.get(owner, generation_id)
        if not self.buffer.has_channel(generation_id) and record["status"] in TERMINAL:
            # The local replay buffer is gone (for example after restart). A
            # completed record still has a canonical result the client can fetch.
            code = "REPLAY_EXPIRED" if record["status"] == "completed" else record.get("errorCode") or "STREAM_INTERRUPTED"
            yield GenerationEvent(generation_id=generation_id, sequence=max(after + 1, record["sequence"] + 1), type="generation.error", data={"code": code, "result": record.get("result")})
            return
        self._attach(generation_id)
        try:
            async for event in self.buffer.subscribe(generation_id, after, record["status"] in TERMINAL):
                yield event
        finally:
            self._detach(owner, generation_id)
