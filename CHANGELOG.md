# Changelog

All notable changes are recorded here. This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic version tags for published releases.

## [Unreleased]

### Added

- Learn workflow with Ask/Learn mode, teaching gears, resumable learner journeys, inline assessment, and a direct path into Quiz.
- Quiz workspace with generated question sets, answer evaluation, repair guidance, and evidence admission through the canonical learner-state service.
- Local privacy controls to export learner records as JSON or permanently remove locally stored learner data and imported materials.
- Desktop provider setup backed by the operating system credential store, a first-run setup screen, native workspace settings menu, and optional due-review notifications.
- Electron desktop packaging for a bundled web interface and FastAPI sidecar, per-user application-data directories, dynamic loopback ports, loopback-token protection, sidecar recovery, and GitHub Actions packaging workflows.
- Signed-beta release automation for Windows x64 and macOS Intel/Apple Silicon, with signing/notarization gates, release checksums, beta release notes, and an upgrade-validation runbook.

### Changed

- Updated the repository README and installation guide around the local desktop beta and GitHub Releases distribution.

### Known limitations

- `v0.1.0-beta` is publishable only after the repository signing and notarization secrets are configured; no public installer exists until that release workflow passes.
- Silent Squirrel uninstall needs final verification through a normal interactive Windows installation; learner data is intentionally preserved across uninstall/reinstall.
- Hosted accounts, synchronization, automatic updates, calibrated mastery, and retrieval-backed source verification are not included.
