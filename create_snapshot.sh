#!/bin/bash
set -e

# --- Configuration ---
PROJECT_DIR="/home/mativiters/1/xsarena"
OUTPUT_DIR="$HOME/snapshot_chunks_$(date '+%Y%m%d-%H%M%S')"
CHUNK_SIZE="100k" # 100 kilobytes
FOOTER_MESSAGE="say received. do nothing else"

# --- Main Script ---
echo "Starting snapshot process..."
echo "Project Directory: $PROJECT_DIR"
echo "Output Directory:  $OUTPUT_DIR"

# Create a temporary file to hold the full snapshot content
TEMP_SNAPSHOT_FILE=$(mktemp)
# Ensure the temporary file is cleaned up on exit
trap 'rm -f "$TEMP_SNAPSHOT_FILE"' EXIT

echo "1. Finding and collecting relevant project files..."

# Find all relevant files and append them to the temporary file with headers
# This EXCLUDES irrelevant directories like .git, venv, and the unrelated Go project
find "$PROJECT_DIR" -type f \
  -not -path '*/.git/*' \
  -not -path '*/venv/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.pytest_cache/*' \
  -not -path '*/.ruff_cache/*' \
  -not -path '*/src/gomobile-matsuri-src/*' \
  -not -path '*/snapshot_chunks/*' \
  -not -name '*.pyc' \
  -not -name '*.tar.gz' \
  -not -name 'snapshot_*.txt' \
  -print0 | while IFS= read -r -d $'\0' file; do
    # Get the file path relative to the project directory
    relative_path="${file#"$PROJECT_DIR/"}"
    
    # Write file header and content to the temporary snapshot file
    echo "--- START OF FILE $relative_path ---" >> "$TEMP_SNAPSHOT_FILE"
    cat "$file" >> "$TEMP_SNAPSHOT_FILE"
    echo "" >> "$TEMP_SNAPSHOT_FILE" # Ensure a newline at the end of the content
    echo "--- END OF FILE $relative_path ---" >> "$TEMP_SNAPSHOT_FILE"
    echo "" >> "$TEMP_SNAPSHOT_FILE" # Add a blank line for readability
done

echo "2. Splitting the snapshot into ${CHUNK_SIZE} chunks..."

# Create the output directory
mkdir -p "$OUTPUT_DIR"

# Split the temporary file into chunks
split -b "$CHUNK_SIZE" -d --additional-suffix=.txt "$TEMP_SNAPSHOT_FILE" "$OUTPUT_DIR/chunk_"

echo "3. Appending required footer to each chunk..."

# Add the required footer message to each chunk file
for chunk_file in "$OUTPUT_DIR"/chunk_*.txt; do
  echo "$FOOTER_MESSAGE" >> "$chunk_file"
done

echo "-----------------------------------------------------"
echo "✅ Snapshot created successfully!"
echo "Chunks are located in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"
echo "-----------------------------------------------------"