#!/bin/bash
# Agent Locking Protocol for XSArena
# Provides file-based locking mechanism to prevent multiple agents from overwriting each other's work

LOCK_DIR=".xsarena/locks"
LOCK_TIMEOUT=300  # 5 minutes timeout
MAX_WAIT_TIME=600 # 10 minutes maximum wait time

# Function to acquire a lock
# Usage: acquire_lock <lock_name> [timeout_in_seconds]
acquire_lock() {
    local lock_name="$1"
    local timeout="${2:-$LOCK_TIMEOUT}"

    # Create lock directory if it doesn't exist
    mkdir -p "$LOCK_DIR"

    local lock_file="$LOCK_DIR/$lock_name.lock"
    local start_time=$(date +%s)
    local current_time=$start_time

    # Try to create the lock file using a temporary file and atomic move
    while [ $((current_time - start_time)) -lt $MAX_WAIT_TIME ]; do
        # Create a temporary file with our process info
        local temp_lock="/tmp/xsarena_lock_${lock_name}_$$"
        echo "$(date): Process $$ on $(hostname)" > "$temp_lock"

        # Try to atomically move it to the lock location
        if mv "$temp_lock" "$lock_file" 2>/dev/null; then
            echo "Lock acquired: $lock_name"
            return 0
        fi

        # Check if the existing lock is stale (older than timeout)
        if [ -f "$lock_file" ]; then
            local lock_time=$(stat -c %Y "$lock_file" 2>/dev/null || echo 0)
            local current_time=$(date +%s)

            if [ $((current_time - lock_time)) -gt $timeout ]; then
                # Lock is stale, remove it and try again
                echo "Removing stale lock: $lock_name"
                rm -f "$lock_file"
                continue
            fi
        fi

        echo "Waiting for lock: $lock_name (will timeout in $((MAX_WAIT_TIME - (current_time - start_time)))s)"
        sleep 5
        current_time=$(date +%s)
    done

    echo "Failed to acquire lock: $lock_name - timeout"
    return 1
}

# Function to release a lock
# Usage: release_lock <lock_name>
release_lock() {
    local lock_name="$1"
    local lock_file="$LOCK_DIR/$lock_name.lock"

    if [ -f "$lock_file" ]; then
        # Only release the lock if we own it (same process ID)
        local lock_content=$(cat "$lock_file" 2>/dev/null)
        if [[ "$lock_content" == *$$* ]]; then
            rm -f "$lock_file"
            echo "Lock released: $lock_name"
        else
            echo "Warning: Cannot release lock $lock_name - not owned by this process"
        fi
    fi
}

# Function to check if a lock exists
# Usage: is_locked <lock_name>
is_locked() {
    local lock_name="$1"
    local lock_file="$LOCK_DIR/$lock_name.lock"

    if [ -f "$lock_file" ]; then
        local lock_time=$(stat -c %Y "$lock_file")
        local current_time=$(date +%s)
        local age=$((current_time - lock_time))

        if [ $age -lt $LOCK_TIMEOUT ]; then
            echo "true"
            return 0
        else
            # Lock is stale, remove it
            rm -f "$lock_file"
            echo "false"
            return 1
        fi
    else
        echo "false"
        return 1
    fi
}

# Function to list all active locks
list_locks() {
    if [ -d "$LOCK_DIR" ]; then
        for lock_file in "$LOCK_DIR"/*.lock; do
            if [ -f "$lock_file" ]; then
                local lock_name=$(basename "$lock_file" .lock)
                local lock_time=$(stat -c %Y "$lock_file")
                local current_time=$(date +%s)
                local age=$((current_time - lock_time))

                echo "Lock: $lock_name, Age: $age seconds, Created: $(date -d @$lock_time)"
            fi
        done
    else
        echo "No locks directory found"
    fi
}

# Example usage:
# acquire_lock "snapshot_operation" 300
# # Do work here
# release_lock "snapshot_operation"

# For command line usage:
case "${1:-help}" in
    acquire)
        if [ -n "$2" ]; then
            acquire_lock "$2" "${3:-$LOCK_TIMEOUT}"
        else
            echo "Usage: $0 acquire <lock_name> [timeout]"
            exit 1
        fi
        ;;
    release)
        if [ -n "$2" ]; then
            release_lock "$2"
        else
            echo "Usage: $0 release <lock_name>"
            exit 1
        fi
        ;;
    check)
        if [ -n "$2" ]; then
            is_locked "$2"
        else
            echo "Usage: $0 check <lock_name>"
            exit 1
        fi
        ;;
    list)
        list_locks
        ;;
    help)
        echo "XSArena Agent Locking Protocol"
        echo "Usage:"
        echo "  $0 acquire <lock_name> [timeout] - Acquire a lock"
        echo "  $0 release <lock_name>           - Release a lock"
        echo "  $0 check <lock_name>             - Check if lock exists"
        echo "  $0 list                          - List all active locks"
        echo "  $0 help                          - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
