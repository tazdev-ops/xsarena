#!/bin/bash
set -e

# --- Configuration ---
PROJECT_DIR="/home/mativiters/1/xsarena"
OUTPUT_DIR="$HOME/targeted_snapshot_$(date '+%Y%m%d-%H%M%S')"
CHUNK_SIZE="100k"
FOOTER_MESSAGE="say received. do nothing else"

# --- Main Script ---
echo "Starting targeted snapshot process..."
TEMP_SNAPSHOT_FILE=$(mktemp)
trap 'rm -f "$TEMP_SNAPSHOT_FILE"' EXIT

echo "1. Finding and collecting relevant project files (with exclusions)..."

# This find command now explicitly EXCLUDES the large, irrelevant directories
find "$PROJECT_DIR" -type f \
  -not -path '*/.git/*' \
  -not -path '*/venv/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.pytest_cache/*' \
  -not -path '*/.ruff_cache/*' \
  -not -path '*/src/gomobile-matsuri-src/*' \
  -not -path '*/snapshot_chunks/*' \
  -not -path '*/legacy/*' \
  -not -name '*.pyc' \
  -not -name '*.tar.gz' \
  -not -name 'snapshot_*.txt' \
  -print0 | while IFS= read -r -d $'\0' file; do
    relative_path="${file#"$PROJECT_DIR/"}"
    echo "--- START OF FILE $relative_path ---" >> "$TEMP_SNAPSHOT_FILE"
    cat "$file" >> "$TEMP_SNAPSHOT_FILE"
    echo "" >> "$TEMP_SNAPSHOT_FILE"
    echo "--- END OF FILE $relative_path ---" >> "$TEMP_SNAPSHOT_FILE"
    echo "" >> "$TEMP_SNAPSHOT_FILE"
done

echo "2. Splitting the snapshot into chunks..."
mkdir -p "$OUTPUT_DIR"
split -b "$CHUNK_SIZE" -d --additional-suffix=.txt "$TEMP_SNAPSHOT_FILE" "$OUTPUT_DIR/chunk_"

echo "3. Appending required footer to each chunk..."
for chunk_file in "$OUTPUT_DIR"/chunk_*.txt; do
  echo "$FOOTER_MESSAGE" >> "$chunk_file"
done

echo "-----------------------------------------------------"
echo "✅ Targeted snapshot created successfully!"
echo "Chunks are located in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"
echo "-----------------------------------------------------"