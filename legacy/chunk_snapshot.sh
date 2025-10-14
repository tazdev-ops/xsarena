#!/usr/bin/env bash
# Script to chunk the snapshot file into 350KB chunks with message (300-400KB range)
INPUT_FILE="${1:-$HOME/xsa_min_snapshot.txt}"
CHUNK_SIZE="${2:-350000}"  # 350KB default to fit 300-400KB range
OUTPUT_DIR="$HOME/snapshot_chunks"

mkdir -p "$OUTPUT_DIR"

# Use split to break the file into chunks
split -b${CHUNK_SIZE} "$INPUT_FILE" "$OUTPUT_DIR/chunk_"

# Process each chunk to append the message
for chunk in "$OUTPUT_DIR"/chunk_*; do
  echo -e "\\n\\nJust say received. do nothing. i will send you the rest of the code\\n" >> "$chunk"
done

echo "Chunked $INPUT_FILE into $OUTPUT_DIR/ with $(ls -1 $OUTPUT_DIR/chunk_* 2>/dev/null | wc -l) chunks"