# Materials and context: first implementation

Updated: 13 September 2026

This is the first runnable local increment of `Materials_Context_and_Practice_Implementation_Spec.md`, not completion of all nine work packages. Existing Python/FastAPI, SQLAlchemy/Alembic, and web components are preserved. No deployment or live paid-model validation was performed.

## What works

- The Learn view has a **Supporting materials** panel: upload PDF/TXT/Markdown, classify material role, select materials, inspect extracted passages, delete materials, and ask a question against the selection.
- Immutable uploads have opaque file keys, SHA-256 hashes, owner scope, a 50 MiB limit, and durable ingestion jobs. File content is stored under `backend/data/materials` by default; metadata, passages, attachments, jobs, and context manifests are in the configured application database.
- UTF-8 and text PDF extraction preserve passage order and zero-based physical page indexes. Blank/image pages are reported as requiring OCR; mixed PDFs are partially ready. Layout, diagrams, equations, and printed page labels are not claimed to be understood.
- A local worker claims jobs with leases, bounded attempts, and recovery of expired work. Upload routes also schedule one background processing attempt. Run the worker for reliable queue draining and recovery after application restarts.
- Retrieval is lexical overlap across explicitly attached, authorized, ready materials, limited to six passages and a 16,000-byte evidence budget. The complete prompt has additional instructions, the bounded question, and learner context; the evidence byte budget is not a model token-window guarantee.
- Answer keys and sample papers are excluded from teaching retrieval. A paper may contain inline solutions, so it stays excluded until question/solution separation exists.
- A configured server-side provider receives the actual question, retrieved text, teaching gear, and canonical learner evidence. With no provider, the application returns source excerpts only. Answers are explicitly unverified; there is no automatic mastery admission.
- Each retrieval writes a context manifest containing source/version/page references, query hash, limits, and retrieval method. It does not duplicate passage text. Manifest access rechecks ownership and material availability.
- Normal teaching actions now project canonical learner state instead of trusting visualization activity as evidence. The model receives the actual request and teaching profile. Provider reasoning-only responses are rejected as answers.
- Source and manifest access fail closed after deletion. Deletion removes original bytes, extracted passages, and attachments and cancels associated ingestion work. Already displayed browser content is not remotely retractable.

## Local startup

From the project root, in separate terminals:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
.\backend\.venv\Scripts\python.exe -m backend.app.material_worker
```

```powershell
Set-Location web
npm run dev
```

Use the same `DATABASE_URL`/`FORMA_DB_PATH` and `AI_TUTOR_MATERIAL_DIR` values in API and worker terminals. The worker does not require model credentials. Existing provider configuration remains on the backend. For a single recovery step, use `python -m backend.app.material_worker --once`.

Schema migration `0005_material_context` runs through existing Store startup. It adds material tables and reserved context/practice record tables; reserved practice tables do not mean practice generation is implemented.

Local ownership uses `X-Dev-Learner-Id`, defaulting to `local`, consistently with learner-state routes. This is a development convention, not authentication. Material routes reject production/deployed environments. The existing application is not ready for public hosting.

## API surface

| Route | Purpose |
|---|---|
| `POST /v1/materials` | Declare upload title, mediaType, byteCount, role |
| `PUT /v1/materials/{id}/versions/{version}/content` | Stream original bytes to an immutable version |
| `POST /v1/materials/text` | Upload pasted UTF-8 text |
| `GET /v1/materials`, `GET /v1/materials/{id}` | List materials and inspect extraction status |
| `DELETE /v1/materials/{id}` | Delete bytes and extracted data |
| `GET /v1/material-versions/{id}/blocks` | Inspect extracted passages |
| `GET /v1/source-spans/{id}` | Resolve an authorized passage |
| `GET /v1/material-jobs/{id}`, `POST .../{id}/retry` | Job status and bounded retry |
| `POST /v1/sessions/{id}/materials` | Attach materialVersionId |
| `DELETE /v1/sessions/{id}/materials/{version}` | Detach material |
| `POST /v1/sessions/{id}/material-answer` | Retrieve and optionally explain a message |
| `GET /v1/context-manifests/{id}` | Inspect selected source references and retrieval limits |

The material-answer endpoint is separate from ordinary teaching actions. Its UI currently starts a dedicated material session per question. Generated material answers are displayed in browser state; durable transcripts and checkpoint resumption remain pending. Retrieved passages are context references, not claim-level citations proving every sentence.

## Next implementation sequence

1. Finish WP0–WP2 integration: one teaching action path, scoped source manifests on artifacts, full prompt token accounting, resource authorization across existing session/lesson endpoints, richer retrieval evaluation, and claim-to-span validation.
2. Complete WP3: durable ordered turns, branch-local histories, checkpoint compaction, restore UI, idempotent commands, and material-version invalidation of derived content.
3. WP4–WP5: parse sample papers into reviewed question/solution objects and explicit blueprint revisions; then generate constrained practice with independent validation and separate private solutions. Do not enable the reserved practice contracts before these checks exist.
4. WP6–WP7: durable attempts, reveal policy, deterministic or calibrated assessment, and evidence admission through the canonical reducer.
5. WP8: verified authentication, hosted object storage, parser isolation and OCR, PostgreSQL concurrency tests, resource quotas, deletion retention policy, observability, and deployment.

Do not describe this increment as semantic search, OCR, verified tutoring, adaptive sample-paper generation, persistent chat memory, or production authentication. Those are still outstanding work from the specification.

## Validation

The full offline backend suite passed: **52 tests**. After adding manifest checks and the mocked material-answer integration, all **6 material tests** passed again. Coverage includes legacy migration preservation, canonical evidence authority, upload validation, immutable content, ownership, deletion, blank PDFs, recovery, attachment-scoped retrieval, evidence budgets, answer-key exclusion, and provider output handling.

Frontend TypeScript checking, targeted ESLint, and the full five-stage web build passed. The build reports the existing Vinext static route-classification limitation. Provider integration uses mocked responses; no real provider quality/latency evaluation, PostgreSQL concurrency test, or browser interaction test has been run.
