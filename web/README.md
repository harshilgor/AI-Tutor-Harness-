# Forma learning workspace

This folder contains the first interactive website for the AI Tutor Harness. It is a minimal, local-first learning workspace inspired by Cursor, Notion, and Apple.

## What is working

- Home workspace with topic entry, sample map library, resume state, and local draft-graph generation.
- Three authored sample knowledge maps: Thinking in systems, The language of light, and Foundations of calculus.
- Map view with concept relationships, zoom controls, and a learn path.
- Lesson view with Quick, Guided, and Deep teaching gear.
- Contextual explorations that open beside the lesson, can nest one level deeper, and save on the device.
- Short understanding checks, saved lessons, related reading, and WebMCP actions for opening sample maps and reading workspace state.
- Responsive layouts for desktop and small screens.

## Current boundary

This release combines an interaction preview with the first local backend slice. Arbitrary topics can produce a persisted seven-concept draft graph through FastAPI, but the deterministic provider has no retrieved sources and is labeled limited/unverified. Model-provider calls, authentication, evidence-backed mastery, and assessment generation remain planned backend work.

## Backend integration seam

`lib/api.ts` contains the browser-side, provider-neutral contract for the next slice. It defines versioned graph concepts and edges, source provenance and trust states, learner overlays, topic-scope clarification, lesson blocks, teaching actions, run status, sidecar branches, attempts, and notes. The `learningApi` client targets `/v1` resources by default; set `NEXT_PUBLIC_LEARNING_API_URL` when the FastAPI service runs at another origin. The sample UI remains independent of this client until the API can return approved, source-aware artifacts.

## Run locally

```bash
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The broader product and technical decisions live one directory up in the phase-one briefs.
