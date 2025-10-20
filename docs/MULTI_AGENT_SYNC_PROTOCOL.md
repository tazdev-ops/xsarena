# XSArena Multi-Agent Synchronization Protocol

## Overview
This document describes the synchronization protocol for multiple agents working with the XSArena tool. The protocol prevents conflicts when multiple agents (human users, AI agents, scripts) are working on the same project simultaneously.

## File-Based Locking System

### Components
- **Lock Directory**: `.xsarena/locks/` - Contains all active lock files
- **Lock Files**: Named `<lock_name>.lock` - Created when a resource is locked
- **Lock Timeout**: 5 minutes by default - Locks are considered stale after this time
- **Max Wait Time**: 10 minutes - Maximum time to wait for a lock before giving up

### Lock Types
Different types of operations should use different lock names:

1. **`snapshot_operation`** - For snapshot creation operations
2. **`handoff_operation`** - For handoff preparation operations
3. **`orders_operation`** - For orders management operations
4. **`job_execution`** - For job execution operations
5. **`config_modification`** - For configuration changes
6. **`custom_operation_name`** - For other operations that need synchronization

### Usage Pattern

#### For Scripts/Agents
```bash
# Before performing an operation that needs synchronization
if tools/agent_locking_protocol.sh acquire snapshot_operation 300; then
    # Perform your operation here
    xsarena ops snapshot create --mode author-core --out ~/repo_flat.txt
    # Release the lock when done
    tools/agent_locking_protocol.sh release snapshot_operation
else
    echo "Could not acquire lock, operation cancelled"
    exit 1
fi
```

#### For Command Line
```bash
# Check if a lock exists
tools/agent_locking_protocol.sh check snapshot_operation

# List all active locks
tools/agent_locking_protocol.sh list

# Manually release a lock if needed
tools/agent_locking_protocol.sh release snapshot_operation
```

## Recommended Usage for Multiple Agents

### 1. CLI Agent Protocol
When the CLI agent receives a command that modifies the project state:

1. Acquire the appropriate lock before starting the operation
2. Perform the operation
3. Release the lock when finished
4. Handle lock acquisition failures gracefully

### 2. Higher AI Protocol
When the Higher AI needs to perform operations:

1. Acquire the appropriate lock
2. Verify the current project state
3. Perform the operation
4. Release the lock

### 3. Concurrency Guidelines

- **Snapshot Operations**: Use `snapshot_operation` lock
- **Handoff Operations**: Use `handoff_operation` lock
- **Orders Operations**: Use `orders_operation` lock
- **Job Operations**: Use `job_execution` lock
- **Configuration Changes**: Use `config_modification` lock

## Error Handling

### Lock Acquisition Failure
If an agent cannot acquire a lock:
1. Wait and retry if appropriate
2. Report the conflict to the user/Higher AI
3. Suggest manual resolution if needed

### Stale Locks
The protocol automatically detects and removes stale locks (older than timeout). However, agents should:
1. Always release locks when operations complete
2. Handle unexpected termination to avoid leaving stale locks

## Integration Examples

### Integration with Snapshot Commands
```bash
# Before running a snapshot command
if tools/agent_locking_protocol.sh acquire snapshot_operation; then
    xsarena ops snapshot create --mode author-core --out ~/repo_flat.txt
    tools/agent_locking_protocol.sh release snapshot_operation
fi
```

### Integration with Handoff Commands
```bash
# Before preparing a handoff
if tools/agent_locking_protocol.sh acquire handoff_operation; then
    xsarena ops handoff prepare --note "Handoff for issue resolution"
    tools/agent_locking_protocol.sh release handoff_operation
fi
```

## Best Practices

1. **Always Release Locks**: Ensure locks are released even in error conditions
2. **Use Appropriate Timeouts**: Set timeouts appropriate for the operation duration
3. **Be Specific with Lock Names**: Use descriptive names that reflect the operation
4. **Handle Conflicts Gracefully**: Don't fail catastrophically when locks can't be acquired
5. **Monitor Active Locks**: Regularly check for stale locks that may need manual cleanup

## Implementation Notes

The locking protocol is implemented as a bash script for maximum compatibility across different systems and agents. The script uses atomic file operations to ensure thread safety across different processes.

The protocol does not require any external dependencies beyond standard Unix tools (mv, stat, rm, etc.) and is designed to work in multi-user environments where different agents may be running as different processes.
