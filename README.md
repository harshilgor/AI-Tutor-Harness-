# AI Tutor Harness

Start the local web interface and tutor API together with `./start-local.ps1` from PowerShell. Opening the web interface alone does not start the Python API. Startup logs are saved in `work/local-runtime`.

An AI learning environment that combines a curriculum graph, persistent learner evidence, adaptive teaching, verification, and assessment.

Start with the [Product and Technical Brief](AI_Tutor_Harness_Product_and_Technical_Brief.md).

Before implementation, review [Phase One: Scope and Build Readiness](Phase_One_Scope_and_Build_Readiness.md). It narrows the current scope to the knowledge graph, teaching harness and controls, and contextual exploration windows, and records decisions still needed before coding.

The detailed build reference is [Phase One — Features and Technical Implementation Specification](Phase_One_Features_and_Technical_Implementation_Spec.md). It includes arbitrary-topic graph generation and trust, teaching policies, controls, nested exploration, data/API contracts, reliability, quality gates, and implementation work packages.

Deferred capabilities and architectural extension points are in [Future Features and Technical Considerations](Future_Features_and_Technical_Considerations.md).

The brief consolidates the design conversation into product direction, Learn/Practice/Notebook navigation, the learning kernel and modular architecture, proposed Python/TypeScript stack, assessment generation, data contracts, implementation phases, risks, and open decisions.

The first website slice is in [`web/`](web/). See [`web/README.md`](web/README.md) for the working interactions and [`web/IMPLEMENTATION_STATUS.md`](web/IMPLEMENTATION_STATUS.md) for the current boundary between the interactive preview and the backend work still to connect.

The first backend slice is in [`backend/`](backend/). It provides the local FastAPI graph flow, SQLite persistence, typed graph records, and the deterministic provider boundary described in [`backend/README.md`](backend/README.md).

**Status:** Design baseline plus interactive website, learning-kernel action flow, learner-wide graph projection, and persistent learner-state/evidence infrastructure, version 0.5, 12 September 2026. The backend supports PostgreSQL with migrated SQLite local tests and runs a deterministic teaching path without an API key; source-backed model teaching, calibrated knowledge tracing, authentication, and hosted publishing remain next.
