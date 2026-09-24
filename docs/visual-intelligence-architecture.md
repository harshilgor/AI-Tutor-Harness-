# Visual Intelligence: Architecture Report

## Repository inspection (before implementation)

1. **Agent architecture.** This is a Python/FastAPI tutor organized around service modules, not a general autonomous agent loop. `JourneyService` in `backend/app/journey_service.py` composes context, policy, provider generation, lesson artifacts, and persistence. Tool activity currently includes web evidence search surfaced as `tool.started`/`tool.completed` generation events.
2. **Skills/tools.** No reusable visualization skill registry surfaced in the inspected backend modules. Teaching instructions and structured JSON contracts are assembled in services; tools are explicit service capabilities rather than a generic frontend-code execution system.
3. **Message rendering.** `web/components/learn-chat.tsx` owns Ask/Learn turns and hands completed/streaming blocks to `LessonReader`; `RichContent` (`web/components/rich-content.tsx`) renders Markdown with GFM and safe KaTeX, and skips HTML.
4. **Streaming.** `GenerationManager` emits durable generation state over FastAPI SSE (`generation_routes.py`, `generation_service.py`). Events are sequenced/replayable; lesson content uses `lesson.block_started` and `lesson.block_completed`. Browser reconnection is handled by `web/lib/generation-stream.ts`.
5. **Learn persistence.** Journeys/turns and their generation references are stored as workflow records; lessons are typed `LessonArtifact` blocks persisted by journey/generation services. Session and workflow persistence use SQLAlchemy-backed storage/migrations. Notes have separate study/workspace note services and APIs; Learn lesson filing is currently mediated by `LearnChat`.
6. **Math rendering.** KaTeX via `remark-math` + `rehype-katex` is already configured in `RichContent`, with normalization in `web/lib/normalize-math-markdown.ts`. This typesets equations but does not plot functions.
7. **Visualization today.** No unified visualization spec/renderer surfaced in inspected app files. The concept graph in Learn is a navigable learning map, not an inline chart/diagram renderer.
8. **Reusable dependencies.** Web already depends on Recharts, KaTeX, Zod, React Markdown, and Motion. Recharts covers quantitative chart primitives; SVG/React can provide deterministic diagrams and safe sampled function plots. No need to add a charting dependency for the first implementation.
9. **Missing infrastructure.** Versioned visualization schema and validation; renderer registry; safe math expression evaluator; generated visual event and durable artifact path; inline rendering in chat/lesson; explicit simulation interaction contracts.
10. **Integration points.** Add provider-neutral Pydantic visualization contracts and validation near generation models; ask the existing provider for structured visual specs alongside lesson blocks; emit validated specs on the current SSE channel; render from a registry in `LessonReader`/`LearnChat`.
11. **Database proposal.** Initially store validated visualization JSON as part of the lesson block/turn artifact (or a typed block payload) to preserve atomic lesson revisions and avoid a standalone table. Add a migration only if existing artifact JSON cannot carry versioned content.
12. **API proposal.** Add a `visualization.ready` generation event; include the final validated visualization array in the persisted lesson artifact and normal journey response. Invalid specs should be omitted with a nonfatal fallback.
13. **Frontend proposal.** Add a shared `VisualizationRenderer` with registry, chart renderers (Recharts), SVG diagram renderers, safe math plotting, and bounded controls for simulation. Reuse app theme tokens and respect reduced motion.
14. **Agent/skill proposal.** Add a visual decision/planning instruction and structured spec contract to the existing tutor generation flow. Model supplies data/relationships; app validates and renders. No arbitrary HTML, JSX, or executable JS.

## Implementation sequence

Define versioned schema and bounded validation, implement safe deterministic renderers, integrate structured planning with the current provider/SSE and lesson artifact path, then render persisted and streaming artifacts in Learn. No new dependencies are anticipated.
