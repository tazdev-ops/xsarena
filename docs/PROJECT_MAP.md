# XSArena Project Map

## Getting Started
- `README.md`: Project overview and quick start
- `docs/USAGE.md`: Usage instructions and examples
- `docs/ARCHITECTURE.md`: Detailed system architecture

## Core Directories

### Source Code (`src/xsarena/`)
- `cli/`: Command-line interface (Typer-based)
- `core/`: Core runtime (orchestrator, jobs, backends, state management)
- `bridge_v2/`: FastAPI bridge server for AI communication
- `modes/`: Specialized application modes (book, bilingual, policy, etc.)
- `utils/`: Utility functions and analysis tools

### Configuration & Data
- `directives/`: Prompt templates, overlays, and role guides
- `.xsarena/`: Runtime data (config.yml, session_state.json, job artifacts)
- `recipes/`: Job recipe definitions
- `books/`: Generated book outputs

### Documentation
- `docs/`: Comprehensive documentation (user guides, developer docs, workflows)
- `docs/_help_*.txt`: Generated CLI help files

## Key Configuration
- `directives/_rules/rules.merged.md`: Team/agent operating rules
- `pyproject.toml`: Project dependencies and configuration
- `COMMANDS_REFERENCE.md`: Complete CLI command reference

## Development & Operations
- `scripts/`: Utility scripts
- `tests/`: Test suite
- `Makefile`: Common development commands
