# XSArena State Management

## State Storage Locations

### `.xsarena/` Directory
The main state directory containing:
- `config.yml`: Persistent configuration settings
- `session_state.json`: Current session state
- `jobs/`: Job execution data and logs
- `tmp/`: Temporary files (ephemeral)
- `agent/`: Agent-specific state (ephemeral)

### Configuration State
- **Location**: `.xsarena/config.yml`
- **Persistence**: Saved across sessions
- **Contents**: Backend settings, API keys (if any), default models
- **Management**: Modified via `xsarena config` and `xsarena backend` commands

### Session State
- **Location**: `.xsarena/session_state.json`
- **Persistence**: Saved across sessions
- **Contents**: Current session data, job progress, UI state
- **Management**: Automatically managed by CLI

## Restart-Proof Design

### Recovery Mechanisms
- `xsarena fix run`: Self-heal configuration/state inconsistencies
- `xsarena snapshot write`: Create full system snapshot for recovery
- `xsarena report quick`: Generate diagnostic bundles for debugging

### Ephemeral Data
- **Location**: `.xsarena/tmp/`, `review/`, `snapshot_chunks/`
- **TTL**: Automatically cleaned by TTL-based sweeper
- **Cleanup**: Managed by `xsarena clean` command

## State Consistency
- All state files use atomic write operations
- Backup mechanisms for critical configuration
- Validation on load to detect corruption
- Automatic recovery from last known good state