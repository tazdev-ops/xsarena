# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Professional documentation system with /docs directory, comprehensive README, and CI workflow
- Bridge parity overhaul: restored full LMArena Bridge v2 functionality with WebSocket, streaming, Cloudflare handling, models, ID capture, attachments/file-bed, tavern/bypass modes, image handling
- ID updater service supporting both `/internal/id_capture/update` and `/update` endpoints
- Enhanced ingestion with 3 modes: `ack`, `synth`, `style`
- Userscript with WebSocket communication and command handling (refresh, reconnect, activate_id_capture, send_page_source)
- All core API endpoints: `/health`, `/ws`, `/v1/chat/completions`, `/internal/request_model_update`, `/internal/update_available_models`, `/internal/start_id_capture`, `/internal/config`, `/v1/models`
- Config loading from both .xsarena/config.yml and legacy config.jsonc
- Job resume functionality from last completed chunk
- Stream timeout handling with configurable timeouts
- Image model support with proper markdown formatting

### Changed
- Simplified CLI surface: audio, policy, workshop, people, joy commands marked as hidden
- Deprecated `control-jobs` command kept as hidden shim pointing to new `jobs` commands
- Updated README with comprehensive documentation and troubleshooting
- Unified "run book" as canonical workflow path
- Enhanced interactive cockpit with profile and overlay management
- Refactored CI workflow with comprehensive linting (Ruff, Black, MyPy) and testing

### Fixed
- Cloudflare detection and handling with automatic refresh
- Bridge v2 WebSocket communication and command handling
- ID capture flow working end-to-end
- Job resumption from last completed chunk
- Config loading and validation with proper base_url normalization
- Prompt caching recursion issue that caused maximum recursion depth exceeded errors

## [0.1.0] - 2025-10-15
### Added
- Report bundle functionality with `xsarena report` command
- Git policy documentation and pre-push checks
- Adaptive inspection suppressions for "learning" capability
- Basic documentation files (ROADMAP, SUPPORT, CONFIG_REFERENCE, MODULES, STATE)
- Sync pack procedure for higher AI handoffs
- Pre-push guard script for code quality checks

### Changed
- Enhanced adapt inspector with suppression capabilities
- Improved CLI context handling in report commands

### Fixed
- Fixed CLI context access in report commands
