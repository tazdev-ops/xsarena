# XSArena Module Structure

## Core Modules

### CLI Layer (`src/xsarena/cli/`)
- `main.py`: Main entry point and command router
- `context.py`: CLI context management
- Command modules (`cmds_*.py`): Individual command implementations

### Core Logic (`src/xsarena/core/`)
- `config.py`: Configuration management
- `redact.py`: Data redaction and privacy protection
- `prompt.py`: Prompt composition and management
- `jobs2_runner.py`: Job execution and management
- `recipes.py`: Recipe handling and processing

### Bridge/Backend (`src/xsarena/bridge/`)
- Integration with external AI services
- Userscript and bridge communication

## Command Modules
- `cmds_adapt.py`: Adaptive inspection and fixes
- `cmds_backend.py`: Backend configuration
- `cmds_book.py`: Book authoring commands
- `cmds_continue.py`: Continue from file tail
- `cmds_debug.py`: Debugging tools
- `cmds_fix.py`: Self-healing configuration
- `cmds_jobs.py`: Job execution
- `cmds_report.py`: Report bundle creation
- `cmds_snapshot.py`: Snapshot tools
- `cmds_modes.py`: Mode toggles
- `cmds_run.py`: Unified runner

## Documentation and Scripts
- `docs/`: User documentation
- `scripts/`: Utility scripts
- `recipes/`: Job recipe definitions
- `directives/`: AI directive files