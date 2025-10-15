#!/usr/bin/env bash
# Healthcheck loop for snapshot utility
# This script verifies that the snapshot utility is working properly and follows best practices

set -euo pipefail

echo "=== Snapshot Utility Healthcheck ==="

# 1. Clean any existing snapshots to avoid inclusion of previous outputs
echo "1. Cleaning existing snapshots..."
find .xsarena/snapshots/ -name "snapshot_*.txt" -delete 2>/dev/null || true
find . -name "snapshot_*.txt" -maxdepth 1 -delete 2>/dev/null || true
echo "   ✓ Existing snapshots cleaned"

# 2. Check that snapshot utility exists
if [ ! -f "tools/snapshot_txt.py" ]; then
    echo "   ✗ ERROR: tools/snapshot_txt.py not found"
    exit 1
fi
echo "   ✓ Snapshot utility exists"

# 3. Run a quick snapshot to verify functionality
echo "3. Running test snapshot..."
python tools/snapshot_txt.py --output .xsarena/snapshots/snapshot_health_test.txt --max-chunk-bytes 200000

# 4. Verify output was created (may be multiple chunks)
snapshot_files=(".xsarena/snapshots/snapshot_health_test.txt")
if [ ! -f ".xsarena/snapshots/snapshot_health_test.txt" ]; then
    # Check if it was chunked
    chunk_files=()
    for file in .xsarena/snapshots/snapshot_health_test__chunk*.txt; do
        if [ -f "$file" ]; then
            chunk_files+=("$file")
        fi
    done
    if [ ${#chunk_files[@]} -gt 0 ]; then
        snapshot_files=("${chunk_files[@]}")
        echo "   ✓ Test snapshot created successfully (chunked)"
    else
        echo "   ✗ ERROR: Snapshot was not created"
        exit 1
    fi
else
    echo "   ✓ Test snapshot created successfully"
fi

# 5. Check size is reasonable (not too small, not including massive outputs)
total_size=0
for file in "${snapshot_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(stat -c%s "$file")
        total_size=$((total_size + size))
    fi
done

if [ $total_size -lt 50000 ]; then
    echo "   ⚠ WARNING: Total snapshot size is very small (${total_size} bytes) - may be missing content"
elif [ $total_size -gt 2000000 ]; then
    echo "   ⚠ WARNING: Total snapshot size is very large (${total_size} bytes) - may include unwanted outputs"
else
    echo "   ✓ Total snapshot size is reasonable (${total_size} bytes)"
fi

# 6. Verify required sections are present in at least one chunk
found_dir_trees=false
found_health_checks=false
found_footer=false

for file in "${snapshot_files[@]}"; do
    if [ -f "$file" ]; then
        content=$(cat "$file")
        if [[ "$content" == *"==== Directory Trees ===="* ]]; then
            found_dir_trees=true
        fi
        if [[ "$content" == *"==== Health Checks ===="* ]]; then
            found_health_checks=true
        fi
        if [[ "$content" == *"Answer received. Do nothing else"* ]]; then
            found_footer=true
        fi
    fi
done

if [ "$found_dir_trees" = true ]; then
    echo "   ✓ Directory trees section present"
else
    echo "   ✗ ERROR: Directory trees section missing"
    exit 1
fi

if [ "$found_health_checks" = true ]; then
    echo "   ✓ Health checks section present"
else
    echo "   ✗ ERROR: Health checks section missing"
    exit 1
fi

if [ "$found_footer" = true ]; then
    echo "   ✓ Footer present"
else
    echo "   ✗ ERROR: Footer missing"
    exit 1
fi

# 7. Clean up test snapshot
for file in "${snapshot_files[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
    fi
done
echo "   ✓ Test snapshot cleaned up"

echo ""
echo "=== Healthcheck Complete: PASSED ==="
echo "Rules to maintain:"
echo "1. Always clean existing snapshots before running new ones"
echo "2. Include project source, config, docs; exclude generated content like books/finals"
echo "3. Verify snapshot contains required sections"
echo "4. Check snapshot size is reasonable (50KB-500KB)"