# Web Evidence — Controlled Production Rollout

Canonical ops guide for the bounded Evidence Retrieval Capability (Exa behind
`WebEvidenceProvider`). This is **not** unrestricted browsing: no arbitrary URL
fetching from the frontend, no additional providers, and no mastery/progress
writes from evidence tools.

Related code: `backend/app/web_evidence/`, migrations `0015`–`0016`, health at
`GET /health` and `GET /health/web-evidence`.

---

## 1. Key exposure (server-only)

| Check | Expected |
| --- | --- |
| `backend/.env` | Gitignored (`.gitignore` `.env` / `.env.*`) |
| `EXA_API_KEY` | Set only in server environment or gitignored `.env` |
| `.env.example` | Placeholder only (`EXA_API_KEY=` with no value) |
| Frontend / desktop bundles | Must not reference `EXA_API_KEY` or call `api.exa.ai` |
| CI workflows | Must not inject or log the live key |
| Audits / logs | Redact via `web_evidence.redact`; never log raw excerpts/keys |

Re-scan before go-live (do **not** print the secret):

```powershell
# Confirm ignore + untracked
git check-ignore -v backend/.env
git ls-files --error-unmatch backend/.env   # must fail

# Exact-value scan excluding .env (run from repo root with a local python helper)
# Prefer hashing: never echo the key into chat, tickets, or CI logs.
```

---

## 2. Production database readiness

### Postgres gate

- Deployed environments (`AI_TUTOR_ENV=production` or `deployed`) already require
  `DATABASE_URL` to start with `postgresql` (`backend/app/database.py`).
- If `AI_TUTOR_WEB_EVIDENCE=true` in a deployed environment, enablement is
  **forced off** unless dialect is PostgreSQL and schema/egress checks pass
  (`backend/app/web_evidence/readiness.py` → `enforce_enablement_gate`).
- Local/dev/test may use SQLite with the Fake provider for unit tests.

### Migration command (through web evidence indexes)

From the repo root, with production `DATABASE_URL` set:

```powershell
$env:AI_TUTOR_ENV = "production"
$env:DATABASE_URL = "postgresql+psycopg://USER:PASS@HOST:5432/DB"
cd backend
python -m alembic upgrade 0016_web_evidence_indexes
```

Current Alembic **head** may be newer than `0016` (currently includes
`0017_recommendation_lifecycle` and `0018_session_authority`).
For a full deploy use:

```powershell
python -m alembic upgrade head
```

Do **not** run `alembic downgrade` in production.

### Pre-deploy schema check

Required tables: `web_tool_calls`, `web_evidence_receipts`, `web_evidence_aliases`,
`web_quota_ledgers`, `web_provider_circuit`.

Required indexes (from `0016`): `ix_web_alias_auth`, `ix_web_receipt_auth`,
`ix_web_tool_inflight`.

After migrate, with the API up (flag still **false**):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/web-evidence
# Expect schemaOk=true, missingTables=[], missingIndexes=[]
```

Or in Python:

```python
from backend.app.storage import Store
from backend.app.database import database_url
from backend.app.web_evidence.readiness import check_schema, evaluate_readiness
store = Store(database_url())
print(check_schema(store))
print(evaluate_readiness(store).as_dict())
```

### Backup-first migration runbook

1. Announce a short write window if the host cannot take online DDL safely.
2. Take a Postgres backup **before** migrate (managed snapshot or `pg_dump`):
   ```bash
   pg_dump --format=custom --file=forma-pre-web-evidence.dump "$DATABASE_URL"
   ```
3. Verify backup restore on a scratch database.
4. Set `AI_TUTOR_WEB_EVIDENCE=false` (feature stays off during migrate).
5. Apply `alembic upgrade 0016_web_evidence_indexes` (or `head`).
6. Run schema readiness check above.
7. Only then configure `EXA_API_KEY` and schedule retention; keep the feature flag
   false until smoke tests pass.
8. Rollback = restore the pre-migrate backup. Do not rely on Alembic downgrade.

---

## 3. Explicit production configuration

**Default:** web evidence is **off** unless `AI_TUTOR_WEB_EVIDENCE` is explicitly
`true` / `1` / `yes` / `on` (`load_web_evidence_config`).

### Required (to enable traffic)

| Variable | Production value |
| --- | --- |
| `AI_TUTOR_ENV` | `production` or `deployed` |
| `DATABASE_URL` | `postgresql+psycopg://...` |
| `AI_TUTOR_WEB_EVIDENCE` | `false` until go-live; then `true` for selected rollout |
| `EXA_API_KEY` | Server-only secret |
| `AI_TUTOR_WEB_PROVIDER` | `exa` |
| `EXA_BASE_URL` | `https://api.exa.ai` |
| `AI_TUTOR_WEB_EGRESS_HOSTS` | `api.exa.ai` (deployed envs are pinned to this host in code) |

### Recommended conservative initials

| Variable | Conservative start |
| --- | --- |
| `AI_TUTOR_WEB_KILL_GLOBAL` | `false` (set `true` to deny before provider) |
| `AI_TUTOR_WEB_KILL_TENANTS` | empty, or list tenants **blocked** |
| `AI_TUTOR_WEB_KILL_COURSES` | empty, or list courses **blocked** |
| `AI_TUTOR_WEB_TIMEOUT_SECONDS` | `12` |
| `AI_TUTOR_WEB_CONNECT_TIMEOUT_SECONDS` | `5` |
| `AI_TUTOR_WEB_MAX_RETRIES` | `1` |
| `AI_TUTOR_WEB_MAX_TOOL_ROUNDS` | `2` |
| `AI_TUTOR_WEB_MAX_TOOL_CALLS_ROUND` | `2` |
| `AI_TUTOR_WEB_MAX_RESULTS` | `3`–`5` |
| `AI_TUTOR_WEB_MAX_CHARS` | `800`–`1200` |
| `AI_TUTOR_WEB_MAX_TOTAL_CHARS` | `4000`–`6000` |
| `AI_TUTOR_WEB_MAX_SEARCHES_TURN` | `1` |
| `AI_TUTOR_WEB_MAX_SEARCHES_SESSION` | `4`–`8` |
| `AI_TUTOR_WEB_MAX_SEARCHES_DAY` | `20`–`40` |
| `AI_TUTOR_WEB_MAX_SEARCHES_TENANT_DAY` | `200`–`500` |
| `AI_TUTOR_WEB_MAX_SEARCHES_GLOBAL_DAY` | `1000`–`5000` |
| `AI_TUTOR_WEB_MAX_OPENS_SESSION` | `2`–`4` |
| `AI_TUTOR_WEB_MAX_CONCURRENCY` | `4`–`8` (per process only) |
| `AI_TUTOR_WEB_RESULT_TTL_SECONDS` | `1800` |
| `AI_TUTOR_WEB_CACHE_TTL_SECONDS` | `600` |
| `AI_TUTOR_WEB_CIRCUIT_FAILURES` | `5` |
| `AI_TUTOR_WEB_CIRCUIT_OPEN_SECONDS` | `60` |
| `AI_TUTOR_WEB_RETENTION_INTERVAL_SECONDS` | `900` |
| `AI_TUTOR_WEB_ALLOW_MODEL_DOMAINS` | `false` |
| `AI_TUTOR_WEB_DENYLIST` | keep homework-helper domains from `.env.example` |

Outbound provider calls assert host ∈ `allowed_egress_hosts` (`ExaWebEvidenceProvider._assert_egress`).

---

## 4. Retention operations

Independent of learner traffic:

```powershell
# From repo root
python -m backend.app.web_evidence.retention_job
# Optional: python -m backend.app.web_evidence.retention_job --limit 500
```

- Structured logs: `web_evidence_retention_summary` / `web_evidence_retention_failed`
  with `correlationId` and purge counts (no excerpts/keys).
- Heartbeat row: `context_records` id/kind `web_evidence_retention_status`.
- Health: `GET /health/web-evidence` → `retention.ok` / `retention.stale`.

### Scheduling on this stack

| Topology | How to schedule |
| --- | --- |
| **Single backend process (default desktop / one API host)** | Windows Task Scheduler or systemd timer every 15 minutes calling the module above. Match `AI_TUTOR_WEB_RETENTION_INTERVAL_SECONDS=900`. |
| **Hosted API VM** | Same timer on the host that holds `DATABASE_URL` credentials; run as the service user. |
| **Multiple API replicas** | Run **one** scheduled job (not per replica) against shared Postgres. Opportunistic `purge_expired(limit=50)` on tool calls remains a backup only. |

There is no Docker/K8s CronJob in-repo; do not invent one unless ops adds it.

---

## 5. Monitoring and alerting

Audit stream logger: `ai_tutor.web_evidence` (`web_evidence_audit …` JSON).
IDs: `correlationId`, `requestId`, `traceId`, `toolCallId`; learner id is hashed.
Redaction strips keys, excerpts, provider refs.

### Dashboards / queries (log-based)

| Signal | How to detect | Alert |
| --- | --- | --- |
| Provider timeout/failure | `eventType=web_search_failed` + `errorCategory` in `{timeout,network,provider_error}` | Rate > 5% of searches / 15m |
| Circuit open | `errorCategory=circuit_open` or policy `circuit_open`; table `web_provider_circuit.opened_until` | Any open > 5m |
| Quota denials | `eventType=tool_call_rate_limited` | Spike vs baseline |
| Schema/policy denials | `tool_call_schema_rejected`, `tool_call_policy_denied` (`reasonCode`) | Sustained assessment/kill spikes unexpected |
| Citation validation | `response_citation_validation_failed` | Any in prod soak |
| Retention failure/staleness | `web_evidence_retention_failed` or `/health/web-evidence` `retention.stale=true` | Immediate |
| Abandoned quota reconcile | retention `stats.quotas` rising continuously | Investigate stuck tool calls |
| Tool-loop rounds | Count `tool_call_proposed` per `correlationId` | > `max_tool_rounds` anomalies |

---

## 6. Controlled production smoke-test runbook

Prereqs: Postgres migrated, flag **off** until step prep, key server-side, retention job runnable, one canary tenant/session.

Keep `AI_TUTOR_WEB_EVIDENCE=false` between destructive toggles unless noted.

### a. Successful bounded search

1. Set `AI_TUTOR_WEB_EVIDENCE=true`, kill switches off, restart API.
2. In Learn (not Quiz), ask a source-seeking question (e.g. “cite the NIST definition of the metre”).
3. **Expected learner-visible:** answer may include `[web:W#]` only for returned evidence; no invented URLs.
4. **Expected audits:** `tool_call_proposed` → `web_search_started` → `web_search_succeeded` (and optionally `citation_rendered`). `retrievalOccurred=true` only if durable receipts exist.

### b. Policy denial in assessment mode

1. Trigger search path with `AuthScope.assessment_mode=true` (Quiz / assessment surface) or unit path covering that flag.
2. **Expected:** denial message that external sources are disabled in assessment; `retrieval_occurred=false`.
3. **Audits:** `tool_call_policy_denied` with `reasonCode=assessment_mode_restricted`. No `web_search_started`.

### c. Global kill-switch before provider

1. Set `AI_TUTOR_WEB_KILL_GLOBAL=true`, restart.
2. Repeat a search-seeking Learn turn.
3. **Expected:** learner-safe disabled message; no Exa egress.
4. **Audits:** `tool_call_policy_denied` / `web_search_disabled` path (`feature_web_evidence_enabled=false`). No `web_search_started`.

### d. Provider-outage fallback without false retrieval claim

1. Break provider (invalid key temporarily, or force circuit open via repeated failures).
2. Ask a question that would search.
3. **Expected:** lesson continues from materials; copy must **not** claim a web search succeeded.
4. **Audits:** `web_search_failed` and/or `provider_fallback_used`; citation validator rejects false “I searched the web” prose (`response_citation_validation_failed` if model claims retrieval).

### e. Citation rendering/validation

1. On a successful search turn, confirm aliases like `W1` map to receipts.
2. Inject or review a response that invents `[web:W9]` / raw URL without receipt.
3. **Expected:** validation failure; UI/prompt path must not present forged citations as verified.
4. **Audits:** `citation_rendered` on valid; `response_citation_validation_failed` on invalid.

### f. Retention job execution

1. `python -m backend.app.web_evidence.retention_job`
2. Exit code `0`; log `web_evidence_retention_summary`.
3. `GET /health/web-evidence` → `retention.ok=true`, `retention.stale=false`.

---

## 7. Deployment scope

**Intended initial deployment: one backend instance** (desktop-local API or a single hosted process), matching the streaming docs’ single-process topology.

If/when multiple replicas share Postgres:

- **Cluster-wide cost/quota control** = Postgres `web_quota_ledgers` (and circuit table).
- **In-process semaphore** (`AI_TUTOR_WEB_MAX_CONCURRENCY`) is **per process only** — it does not hard-cap concurrent Exa calls across replicas.
- Do **not** add Redis or a distributed lock unless product explicitly requires a hard cluster-wide in-flight Exa limit.

---

## 8. Go-live checklist

- [ ] Postgres `DATABASE_URL` verified (`AI_TUTOR_ENV=production|deployed`)
- [ ] Backup taken; Alembic through at least `0016_web_evidence_indexes` (or `head`)
- [ ] `/health/web-evidence` reports `schemaOk=true`
- [ ] Key exposure scan passed; `EXA_API_KEY` server-only; `.env` not tracked
- [ ] `AI_TUTOR_WEB_EVIDENCE=false` at boot of canary host
- [ ] Retention job scheduled (15m); heartbeat healthy once
- [ ] Monitoring/alerts wired for table in §5
- [ ] Smoke tests a–f passed on canary
- [ ] Kill switch tested (`AI_TUTOR_WEB_KILL_GLOBAL`)
- [ ] Conservative tenant/course scope chosen (flag on only for canary; kill lists as needed)
- [ ] Enable flag for canary only; soak; then widen

**Out of scope for this rollout:** unrestricted browsing, arbitrary learner-supplied URLs, frontend Exa access, extra providers, mastery/progress write tools.
