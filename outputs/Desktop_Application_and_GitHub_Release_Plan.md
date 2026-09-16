# AI Tutor Desktop Application and GitHub Release Plan

Version 1.0 · 16 September 2026

## Decision

Build Forma as a desktop application with an Electron shell around the existing React/Vinext interface and FastAPI learning service. Keep the learning engine and API independent of Electron so the same code can later power a hosted web edition.

The first public release is a local-first application. It stores learner state, sessions, quiz history, and imported materials on the user's computer. Users may connect their own model-provider key. Accounts, synchronization, billing, and hosted model access are later product layers.

The strategic product is the learning-agent runtime underneath the desktop shell. The desktop application is the learner's environment; the runtime understands learner state, plans toward an objective, executes teaching and assessment tools, observes results, updates evidence, and replans. This runtime is introduced in stages so the first release remains reliable.

## What comparable products teach us

OpenHands separates a browser-facing interface from an agent server and uses explicit local state directories so separate sessions do not collide. Its documented local launch path can run the GUI server directly or in Docker, which shows the value of keeping the runtime independently operable: https://docs.openhands.dev/overview/quickstart and https://download.plaud.ai/OpenHands/OpenHands/blob/main/docs/DEVELOPMENT.md.

Continue distributes a CLI, IDE integrations, and configuration-driven local-model support. Its offline instructions emphasize disabling anonymous telemetry and selecting a local provider, which is a useful privacy baseline for Forma: https://docs.continue.dev/guides/running-continue-without-internet.

CodePilot demonstrates a practical Electron + React/Next desktop pattern with SQLite in WAL mode, MCP/skills integration, and GitHub Release distribution. The relevant design lesson is the boundary between desktop orchestration, local persistence, and extensible agent capabilities: https://github.com/op7418/CodePilot.

Zed shows the expectations users now have from desktop AI tools: automatic background update downloads, restart-to-apply behavior, visible release channels, and preserved workspace state: https://zed.dev/docs/update and https://zed.dev/releases/stable.

GitHub Copilot's desktop application positions the desktop shell as a workspace for agent tasks, parallel work, and lifecycle actions rather than just a web page in a window: https://docs.github.com/en/copilot/concepts/agents/github-copilot-app.

Electron's own guidance recommends packaging with Forge, signing releases, publishing platform artifacts through GitHub Releases, and using GitHub Actions to build for multiple operating systems. Its public update service requires a public repository, GitHub Releases, and code signing on macOS: https://www.electronjs.org/docs/latest/tutorial/distribution-overview and https://www.electronjs.org/docs/latest/tutorial/tutorial-publishing-updating.

## Target architecture

```text
Electron main process
  ├─ creates the application window
  ├─ starts and supervises the packaged FastAPI sidecar
  ├─ owns native notifications, menus, tray, updates, and shutdown
  ├─ exposes a narrow preload API
  └─ stores secrets through the operating-system keychain

React/Vinext renderer
  ├─ Ask/Learn chat
  ├─ inline understanding checks
  ├─ standalone Quiz workspace
  ├─ materials and settings
  └─ review reminders and progress

FastAPI sidecar
  ├─ LearnJourneyService
  ├─ QuizService and question checker
  ├─ scoped retrieval
  ├─ WorkflowStore and durable jobs
  ├─ LearnerStateService
  └─ SQLite repositories and migrations
```

Inside the sidecar, add an explicit runtime boundary above the existing services:

```text
FormaAgentRuntime
  Context → Plan → Act → Observe → Reflect → Replan
```

The runtime coordinates `LearnJourneyService`, `QuizService`, retrieval, and `LearnerStateService`; it does not replace them. Each iteration creates a durable command and observable event. The model may propose an action, but deterministic code validates permissions, source scope, budgets, and state transitions before executing it or admitting evidence.

The renderer must not access Node, the filesystem, SQLite, or arbitrary child processes. It communicates through the existing HTTP API and a small, typed preload bridge for desktop-only operations. The FastAPI process must bind only to loopback, use a per-install random local token, and reject requests without that token.

The backend keeps the existing service boundaries. Electron is an adapter around the application, not a second implementation of learning logic.

## Repository shape

```text
ai-tutor/
  desktop/
    src/main.ts
    src/preload.ts
    src/backend-process.ts
    src/updater.ts
    src/notifications.ts
  web/
  backend/
  shared/
  migrations/
  .github/workflows/ci.yml
  .github/workflows/release.yml
  docs/INSTALL.md
  docs/DEVELOPMENT.md
  docs/PRIVACY.md
  CHANGELOG.md
  LICENSE
  README.md
```

The current `web/` and `backend/` directories can remain in place initially. Add `desktop/` as a thin shell, then move shared contracts only when duplication appears. Do not create a second desktop-specific quiz or learner-state implementation.

## Local runtime behavior

On first launch, the desktop shell should:

1. Choose an application data directory using the platform convention.
2. Create the SQLite database and run migrations.
3. Generate a local installation identifier and loopback authentication token.
4. Start the bundled FastAPI sidecar on an available loopback port.
5. Wait for a `/health` response before loading the renderer.
6. Show a first-run settings screen for model-provider configuration.
7. Open the main window.

On restart, it should reconnect to the same database and restore the last open learning session. On abnormal exit, it should clean up the child process and leave queued jobs recoverable. On shutdown, it should stop the sidecar gracefully.

The sidecar should be bundled as a platform-specific executable or a hermetic runtime. Users should not need Python, Node, Git, or a terminal to use the installer. A developer mode may continue to run the existing separate web and backend commands.

## Desktop MVP scope

The first release should contain:

- Ask/Learn in one conversation interface.
- Reference-material import and scoped retrieval.
- Guided learning route proposal, start, pause, resume, repair, and Ask switching.
- Inline conceptual checks.
- Standalone five-question adaptive quizzes.
- Single-select, multiple-select, and short written answers.
- Hints, skip, “I don't know,” feedback, retry, and challenge reporting.
- Conservative learner-state updates.
- Durable job recovery after reload or restart.
- Local settings, provider configuration, export, and deletion.
- Optional review reminders through native notifications.

Do not add a plugin marketplace, arbitrary executable skills, team collaboration, cloud sync, rankings, or hosted accounts to this release.

## Skills and agent boundaries

The desktop app should not run arbitrary downloaded skills. Approved capabilities are backend modules with explicit contracts:

- `learn.route`
- `learn.teach`
- `learn.repair`
- `quiz.author`
- `quiz.check`
- `quiz.evaluate`
- `quiz.feedback`
- `learner.read_state`
- `learner.admit_evidence`
- `materials.retrieve`

Each capability has a version, input and output schema, allowed tools, time/token budget, source policy, and evaluation fixtures. Models propose structured results; application code validates ownership, source IDs, concept IDs, budgets, and state transitions. No model receives raw SQL, unrestricted filesystem access, or a tool that directly awards mastery.

The first desktop release exposes this runtime only through bounded Learn and Quiz workflows. Its initial action set is `clarify_goal`, `propose_route`, `teach_step`, `request_check`, `repair`, `summarize`, `author_item`, and `evaluate_answer`. Long-running runs must be pausable, cancellable, resumable, and bounded by time, model calls, and token budgets. The runtime should record the purpose, tool, source scope, and outcome of each autonomous step.

The product can grow in three generations: V1 is the AI Tutor; V2 adds the Learning Agent loop, automatic gap diagnosis, targeted repair, and re-planning; V3 adds approved file, browser, annotation, and computer tools behind explicit user permissions and an audit history. Arbitrary executable plugins remain outside the initial release.

## Security and privacy requirements

- Keep provider keys in the OS credential store, not SQLite or renderer local storage.
- Bind the backend to `127.0.0.1` only.
- Use a random per-install request token between renderer and backend.
- Use Electron context isolation, sandboxed renderer settings, and a narrow preload API.
- Treat imported documents, model output, quiz answers, and retrieved text as untrusted data.
- Redact answers, source text, and provider payloads from logs.
- Make telemetry opt-in; provide a visible disable setting and document exactly what is sent.
- Provide export and delete controls for all local learner data.
- Publish dependency and security update policy.
- Sign Windows and macOS installers before public release.

## GitHub repository and release structure

The repository should contain:

- A README with screenshots, supported platforms, privacy model, and a three-step installation path.
- `docs/INSTALL.md` with Windows and macOS troubleshooting.
- `docs/DEVELOPMENT.md` for contributors running the web and backend separately.
- `docs/ARCHITECTURE.md` describing the shell/renderer/sidecar boundary.
- `docs/PRIVACY.md` describing local storage, provider calls, telemetry, and deletion.
- `CHANGELOG.md` following Keep a Changelog conventions.
- Issue templates for bugs, feature requests, privacy concerns, and security reports.
- A security policy with a private vulnerability-reporting route.
- A contributor guide and code of conduct.

Use semantic version tags such as `v0.1.0`, `v0.2.0`, and `v1.0.0`. Keep unreleased changes in `CHANGELOG.md`, then generate the GitHub Release from the tag. GitHub Releases support release notes and downloadable binary assets directly: https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository.

Each release should include:

- Windows x64 installer.
- macOS Apple Silicon installer.
- macOS Intel installer while supported.
- SHA-256 checksums.
- Source archive automatically generated by GitHub.
- A short “what changed” section.
- A migration/data-compatibility section.
- Known issues and rollback instructions.

## Continuous integration and release workflow

Pull requests should run:

1. Python formatting, type checks, and tests.
2. TypeScript type checks and linting.
3. Web production build.
4. Migration upgrade tests against a fresh SQLite database.
5. Desktop packaging smoke checks.

Pushing a version tag should start a GitHub Actions matrix on Windows and macOS. Each job should build the web bundle, build or collect the FastAPI sidecar, package the Electron application, run an install/start smoke test, generate checksums, and upload artifacts. A protected release job should publish the artifacts only after the matrix passes.

For Electron updates, use the official `autoUpdater` path or the updater integrated with the selected packaging tool. Electron documents `update.electronjs.org` as a free option for public GitHub repositories that publish signed macOS/Windows builds. Updates should download in the background, show release notes, and apply on restart. Do not update while a migration or an active write is in progress.

Linux can be added later through AppImage or distribution packages. Electron's built-in updater does not support Linux, so Linux should use manual releases or a package manager initially: https://www.electronjs.org/docs/latest/api/auto-updater.

## Installation experience

README quick start:

```text
1. Download the installer from the latest GitHub Release.
2. Install Forma.
3. Open Forma and choose a model provider in Settings.
4. Start learning or attach reference material.
```

Developer quick start remains separate:

```text
git clone <repository>
cd ai-tutor
pnpm install
pnpm desktop:dev
```

The installer should not require a provider key to open. It should allow browsing the interface and explain that Learn/Quiz generation requires either a configured remote provider or a supported local model.

## Delivery milestones

### Milestone 1: Desktop spike

Create the Electron shell, load the current renderer, start a development FastAPI process, and implement health-check/restart behavior. No product redesign.

### Milestone 2: Bundled local runtime

Bundle the production web assets and FastAPI sidecar, create platform data directories, run migrations automatically, and verify clean install/restart/uninstall on Windows.

### Milestone 3: Desktop-quality reliability

Add OS keychain storage, loopback authentication, crash recovery, export/delete, native menus, notifications, and a first-run provider setup screen.

### Milestone 4: Signed beta release

Build Windows and macOS installers in GitHub Actions, sign them, publish `v0.1.0-beta`, document known limitations, and test upgrades from two prior versions.

### Milestone 5: Public v1

Add automatic updates, stable migration policy, privacy/telemetry controls, issue templates, support documentation, and a repeatable release checklist.

### Milestone 6: Hosted edition

Reuse the same backend contracts with PostgreSQL, hosted authentication, encrypted provider credentials, synchronization, and server-side notifications. This should be a separate deployment target, not a prerequisite for the local product.

## Acceptance criteria for the first release

A new user should be able to install the application on a clean Windows machine, open it without a terminal, configure a provider, attach a document, start Learn, answer an inline check, start a Quiz, close the app, reopen it, and resume with the same learner state. A release build must be signed, downloadable from GitHub Releases, accompanied by release notes and checksums, and upgrade without losing the local database.

## Recommended next implementation tasks

1. Add the Electron workspace and development launcher.
2. Add a backend health endpoint and loopback-token middleware.
3. Move the SQLite path to a platform-aware application-data directory.
4. Add OS keychain integration for provider credentials.
5. Bundle and supervise the FastAPI sidecar.
6. Add GitHub Actions CI for web, backend, migrations, and desktop packaging.
7. Add Windows packaging first, then macOS signing and notarization.
8. Add updater behavior only after signed beta artifacts work.
