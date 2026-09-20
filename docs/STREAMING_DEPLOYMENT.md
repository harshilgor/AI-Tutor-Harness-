# Streaming deployment

Forma separates generation from observation. `POST /v1/sessions/{id}/generations`
creates one durable generation, while `GET /v1/generations/{id}/events` observes
it over server-sent events. A dropped browser connection must reconnect with
`Last-Event-ID` or `?after=`; it must never repeat the creation request with a
new idempotency key.

## Proxy contract

The event endpoint returns `Content-Type: text/event-stream`,
`Cache-Control: no-cache, no-transform`, and `X-Accel-Buffering: no`. Preserve
these headers, disable response buffering and compression/transformation for
the event route, allow long-lived responses, and flush chunks immediately.
Health checks should create a test generation, observe at least one non-terminal
event before completion, disconnect, then reconnect after the last sequence and
verify that no text is duplicated.

The automated API regression verifies the response headers and replay sequence.
The repository cannot validate the behavior of an external CDN or reverse proxy
that is not part of the checkout, so every hosted environment must run the
disconnect/reconnect smoke test after deployment.

## Process topology

Desktop uses `InMemoryReplayEventStore`, which is appropriate for its single
API process. Multi-process or multi-instance hosting must implement the
`ReplayEventStore` protocol with a shared bounded store and route observation
to that shared event history. Durable generation records remain in SQL; token
deltas do not belong in the primary database. If the replay window expires,
the client reconciles completed work from the canonical Journey.

## Metrics and privacy

Generation records expose queue, context-build, time-to-first-token, completion,
and output-size metrics. Token count and throughput fields are explicitly
estimated until provider usage events are normalized. Metrics contain no prompt
or generated lesson text. Logs should identify generations by ID and error code,
without recording learner content or image bytes.

## Provider verification

Normal CI uses deterministic and mocked provider tests. To validate the current
configured provider and credentials, explicitly enable the credit-consuming
contract test:

```powershell
$env:RUN_LIVE_PROVIDER_TESTS = "true"
python -m pytest backend/tests/test_live_provider_streaming.py -m live_provider
```
