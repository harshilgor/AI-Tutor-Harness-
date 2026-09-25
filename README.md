# AI Tutor Harness · Forma

Forma is a local-first AI learning environment for exploring a topic, learning through a guided conversation, working from your own material, and checking understanding without losing context.

It is built around a simple idea: an AI tutor should support deliberate learning rather than act as an unstructured chat window. Forma keeps the learner's workspace, notes, quiz activity, and review data on the device while providing a path from question to explanation to practice.

> **Project status:** local desktop beta. The application is functional for local learning workflows; hosted accounts, multi-device sync, retrieval-backed verification, calibrated mastery, and automatic updates are not included.

[![Download Open Learn](https://img.shields.io/badge/Download-Open%20Learn-2563eb?style=for-the-badge)](https://github.com/harshilgor/Open-Learn/releases)

Open the newest published release and download the installer for your operating system. Open the downloaded file to install Forma; no terminal or development tools are needed. See the [installation guide](docs/INSTALL.md) for platform-specific steps. Installer downloads will appear after the first signed release is published.

## What Forma does

- **Ask and Learn conversations** with Quick, Guided, and Deep teaching depth.
- **Streaming lessons** with reconnect-safe generation, cancellation, semantic sections, and selection-based follow-up explanations.
- **Source-aware learning** from text, PDFs, public web pages, and supported image formats.
- **Local notes** with automatic saving, Markdown editing, backlinks, and the ability to use selected note text as chat context.
- **Practice and assessment** with generated quizzes, hints, answer feedback, persistent attempts, and review scheduling.
- **Knowledge maps** for browsing connected concepts and moving from a map into a focused lesson.
- **Local-first desktop delivery** through Electron, a loopback-only FastAPI service, and encrypted operating-system credential storage for provider keys.

## How it works

```text
Your question or source material
            ↓
  Forma web workspace (Ask / Learn / Notes / Quiz)
            ↓
 Local FastAPI learning service + SQLite learner data
            ↓
 Deterministic baseline, or an optional configured model provider
```

The default `deterministic_baseline` requires no API key. It produces qualified instructional scaffolds and labels them as limited/unverified. Configure OpenRouter or OpenAI in **Your workspace** when you want model-backed lessons and quizzes.

## Current feature boundary

Forma is intentionally conservative about learning claims:

- Generated lessons do not imply verified facts, source coverage, or mastery.
- Learner evidence is persisted separately from exploration and lesson viewing.
- Public-link imports reject private/loopback destinations, credentials, unsafe redirects, oversized content, and non-text responses.
- Provider keys stay in the desktop operating system's credential store and are never exported with local backups.

Read the [product and technical brief](AI_Tutor_Harness_Product_and_Technical_Brief.md) for product direction, [implementation status](web/IMPLEMENTATION_STATUS.md) for the UI boundary, and [future considerations](Future_Features_and_Technical_Considerations.md) for intentionally deferred work.

## Tech stack

| Area | Technology |
| --- | --- |
| Web workspace | React 19, TypeScript, Vinext/Vite, Tailwind CSS, shadcn-compatible components |
| Interaction design | Motion, Lucide, responsive CSS |
| Local API | FastAPI, SQLAlchemy, Alembic |
| Local data | SQLite by default; PostgreSQL supported for deployed environments |
| Desktop app | Electron with a loopback-only local sidecar |
| Tests | Pytest, ESLint, production web build |

## Development setup

### Prerequisites

- Node.js 22.13 or newer
- Python compatible with the backend requirements
- npm

### Run the local workspace

Create the backend environment and install its dependencies:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Then start the web workspace and local API together from the repository root:

```powershell
.\start-local.ps1
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The local API is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Run the desktop app in development

Start the local services as above, then in another terminal:

```powershell
cd desktop
npm install
npm run dev
```

The desktop shell expects the web workspace at `127.0.0.1:3000` and the API at `127.0.0.1:8000`. See the [desktop development guide](desktop/README.md) for overrides, packaging, and local smoke testing.

## Development

### Web workspace

```powershell
cd web
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
npm run lint
npm run build
```

### Backend

```powershell
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/migrations
```

Live-provider tests are opt-in because they may use a configured, paid, or rate-limited model:

```powershell
$env:RUN_LIVE_PROVIDER_TESTS = "true"
python -m pytest backend/tests/test_live_provider_streaming.py -m live_provider
```

## Project structure

```text
backend/     FastAPI service, persistence, migrations, and backend tests
desktop/     Electron shell and packaging scripts
docs/        Installation, release, deployment, and implementation documentation
web/         React workspace, UI components, and client-side API contracts
```

## Recent updates

- Added durable streaming-generation infrastructure and source ingestion for public URLs.
- Added local workspace notes, note context in chat, and automatic note saving.
- Improved first-run desktop settings responsiveness and added subtle reduced-motion-safe interactions across chat, quiz, dialogs, workspace panels, note drafts, and recommendations.
- Expanded local backup, restore, provider configuration, and review-notification flows.

## Releases and installation

Use the **Download Open Learn** button above to find desktop installers. Release changes are tracked in [CHANGELOG.md](CHANGELOG.md), and maintainers should follow the [release runbook](docs/RELEASING.md).

## Contributing

Contributions are welcome. Please keep changes focused, preserve the local-first and evidence-aware boundaries, add or update tests when behavior changes, and avoid committing credentials, local databases, build output, or `.env` files.

Before opening a pull request, run the relevant checks for the area you changed and explain any intentional product-boundary decisions in the description.

## License

This repository does not currently declare a license. Do not assume reuse rights until a license is added.
