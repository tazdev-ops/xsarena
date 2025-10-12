#!/bin/bash
# XSArena Hygiene Pass - Safe Cleanup Script
# Preserves: books/, .xsarena/, legacy shims, core functionality

set -e  # Exit on any error

echo "🔍 XSArena Hygiene Pass"
echo "========================"

# Phase 0: Safety Check
echo "✓ Checking project state..."
if [ ! -f "xsarena_cli.py" ]; then
    echo "❌ ERROR: xsarena_cli.py not found - wrong directory?"
    exit 1
fi

# Phase 1: Dry-run (list what would be removed)
echo -e "\n📋 DRY-RUN: Files that would be cleaned"
echo "----------------------------------------"

echo "Caches:"
find . -type d \( -name "__pycache__" -o -name ".ruff_cache" -o -name ".pytest_cache" -o -name ".mypy_cache" \) 2>/dev/null | head -20

echo -e "\nCompiled files:"
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) 2>/dev/null | head -20

echo -e "\nOS cruft:"
find . -type f \( -name ".DS_Store" -o -name "Thumbs.db" \) 2>/dev/null | head -10

echo -e "\nEmpty directories (excluding protected paths):"
find . -type d -empty \
    -not -path "./.git*" -not -path "./books*" -not -path "./.xsarena*" -not -path "./snapshot_chunks*" -not -path "." \
    -not -path "./legacy*" -not -path "./src*" 2>/dev/null | head -20

echo -e "\nTemporary snapshot files:"
ls -la snapshot.* 2>/dev/null || echo "No snapshot files found"

# Phase 2: Confirmation and cleanup
echo -e "\n⚠️  WARNING: This will remove the above files."
read -p "Do you want to proceed with cleanup? (yes/no): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n🧹 Performing cleanup..."
    
    # Remove caches
    find . -type d \( -name "__pycache__" -o -name ".ruff_cache" -o -name ".pytest_cache" -o -name ".mypy_cache" \) -prune -exec rm -rf {} + 2>/dev/null || true
    
    # Remove compiled files
    find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name ".DS_Store" -o -name "Thumbs.db" \) -delete 2>/dev/null || true
    
    # Remove temporary snapshot files
    rm -f snapshot.txt snapshot_manual.txt 2>/dev/null || true
    rm -rf snapshot_chunks/ 2>/dev/null || true
    
    # Remove empty directories (excluding protected paths)
    find . -type d -empty \
        -not -path "./.git*" -not -path "./books*" -not -path "./.xsarena*" -not -path "./snapshot_chunks*" -not -path "." \
        -not -path "./legacy*" -not -path "./src*" \
        -delete 2>/dev/null || true
    
    echo "✅ Cleanup completed!"
else
    echo "⏭️  Cleanup skipped."
fi

# Phase 3: Final verification
echo -e "\n✅ Verification:"
echo "  - xsarena_cli.py: $(if [ -f xsarena_cli.py ]; then echo '✓ exists'; else echo '❌ missing'; fi)"
echo "  - src/: $(if [ -d src/ ]; then echo '✓ exists'; else echo '❌ missing'; fi)"
echo "  - legacy/: $(if [ -d legacy/ ]; then echo '✓ exists'; else echo '❌ missing'; fi)"
echo "  - books/: $(if [ -d books/ ]; then echo '✓ exists'; else echo '❌ missing'; fi)"
echo "  - .xsarena/: $(if [ -d .xsarena/ ]; then echo '✓ exists'; else echo '❌ missing'; fi)"

echo -e "\n🎯 Hygiene pass complete!"