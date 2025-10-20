# Changelog

All notable changes to this project will be documented here.
Format: Keep a Changelog. Versioning: SemVer.

## [0.2.0] - 2025-10-20
### Added
- v2 orchestrator (RunSpecV2), resumable jobs, scheduler with quiet hours
- Bridge v2 (FastAPI): WS, per-request refresh guard, per-peer rate limits
- Snapshot tooling: flat pack + verify gate + debug-report

### Changed
- Unified settings (configuration + controls) and modern ID capture commands
- Interactive cockpit: prompt profile/overlay controls, run.inline

### Fixed
- Error mapping for transport errors; consistent verify exit codes; minor CLI polish

## [Unreleased]
- Docs refinements; more presets and examples
