#!/bin/bash

# Script to create a snapshot of the project for AI inspection
# Includes a project tree and relevant code files in a single output file

# Parse command line arguments
DRY_RUN=false
CHUNK_OUTPUT=false
for arg in "$@"; do
    if [ "$arg" = "--dry-run" ] || [ "$arg" = "-n" ]; then
        DRY_RUN=true
    elif [ "$arg" = "--chunk" ] || [ "$arg" = "-c" ]; then
        CHUNK_OUTPUT=true
    fi
done

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN MODE: Showing what would be included in the snapshot without creating it"
    echo
    echo "Project Directory Structure:"
    echo "============================="
    find . -type d | grep -v -E '\./(__pycache__|\.git|build|dist|node_modules|\.pytest_cache|\.vscode|venv|env|\.env)' | sed 's/^\.\///' | sort
    echo
    echo "Project Files to be included:"
    echo "============================="
    find . -type f \
      -not -path "./books/*" \
      -not -path "./__pycache__/*" \
      -not -path "*/__pycache__/*" \
      -not -path "./.git/*" \
      -not -path "*/build/*" \
      -not -path "*/dist/*" \
      -not -path "*/node_modules/*" \
      -not -path "*/.pytest_cache/*" \
      -not -path "*/.vscode/*" \
      -not -path "*/venv/*" \
      -not -path "*/env/*" \
      -not -path "*/.env/*" \
      -not -path "./nexus.txt" \
      -not -path "./book.md" \
      -not -path "./snapshot.txt" \
      -not -path "./temp_*" \
      -not -path "./available_models.json" \
      -not -path "*/.ruff_cache/*" \
      -not -path "./directives/*" \
      -not -path "./pipelines/*" \
      -not -path "./examples/*" \
      -not -path "./docs/*" \
      -not -path "./tests/*" \
      -not -path "./snapshot_chunks/*" \
      | sed 's/^\.\///' | sort
    echo
    echo "Files to be included (code files only):"
    echo "======================================"
    find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.json" -o -name "*.toml" -o -name "*.md" -o -name "*.txt" \) \
      -not -path "./books/*" \
      -not -path "./__pycache__/*" \
      -not -path "*/__pycache__/*" \
      -not -path "./.git/*" \
      -not -path "*/build/*" \
      -not -path "*/dist/*" \
      -not -path "*/node_modules/*" \
      -not -path "*/.pytest_cache/*" \
      -not -path "*/.vscode/*" \
      -not -path "*/venv/*" \
      -not -path "*/env/*" \
      -not -path "*/.env/*" \
      -not -path "./nexus.txt" \
      -not -path "./book.md" \
      -not -path "./snapshot.txt" \
      -not -path "./temp_*" \
      -not -path "./available_models.json" \
      -not -path "*/.ruff_cache/*" \
      -not -path "./directives/*" \
      -not -path "./pipelines/*" \
      -not -path "./examples/*" \
      -not -path "./docs/*" \
      -not -path "./tests/*" \
      -not -path "./snapshot_chunks/*" \
      | sed 's/^\.\///' | sort
    echo
    echo "Files excluded: books/, __pycache__, .git/, build/, dist/, node_modules/, etc."
    echo "DRY RUN COMPLETE: No snapshot file was created"
else
    OUTPUT_FILE="snapshot.txt"
    CHUNK_SIZE=100000  # 100KB in characters

    echo "Creating project snapshot..."

    # Create temporary tree output using a simple find command
    {
      echo "Project Directory Structure:"
      echo "============================="
      find . -type d | grep -v -E '\./(__pycache__|\.git|build|dist|node_modules|\.pytest_cache|\.vscode|venv|env|\.env)' | sed 's/^\.\///' | sort
      echo
      echo "Project Files:"
      echo "=============="
      find . -type f \
        -not -path "./books/*" \
        -not -path "./__pycache__/*" \
        -not -path "*/__pycache__/*" \
        -not -path "./.git/*" \
        -not -path "*/build/*" \
        -not -path "*/dist/*" \
        -not -path "*/node_modules/*" \
        -not -path "*/.pytest_cache/*" \
        -not -path "*/.vscode/*" \
        -not -path "*/venv/*" \
        -not -path "*/env/*" \
        -not -path "*/.env/*" \
        -not -path "./nexus.txt" \
        -not -path "./book.md" \
        -not -path "./snapshot.txt" \
        -not -path "./temp_*" \
        -not -path "./available_models.json" \
      -not -path "*/.ruff_cache/*" \
      -not -path "./directives/*" \
      -not -path "./pipelines/*" \
      -not -path "./examples/*" \
      -not -path "./docs/*" \
      -not -path "./tests/*" \
        -not -path "./snapshot_chunks/*" \
        | sed 's/^\.\///' | sort
    } > temp_tree_output.txt

    # Clear the output file
    > "$OUTPUT_FILE"

    # Add project tree to the output file
    echo "=== PROJECT TREE ===" >> "$OUTPUT_FILE"
    cat temp_tree_output.txt >> "$OUTPUT_FILE"
    echo -e "\n" >> "$OUTPUT_FILE"

    # Add relevant code files to the output file
    echo "=== RELEVANT CODE FILES ===" >> "$OUTPUT_FILE"

    # Find and include relevant source files (excluding books, __pycache__, .git, etc.)
    find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.json" -o -name "*.toml" -o -name "*.md" -o -name "*.txt" \) \
      -not -path "./books/*" \
      -not -path "./__pycache__/*" \
      -not -path "*/__pycache__/*" \
      -not -path "./.git/*" \
      -not -path "*/build/*" \
      -not -path "*/dist/*" \
      -not -path "*/node_modules/*" \
      -not -path "*/.pytest_cache/*" \
      -not -path "*/.vscode/*" \
      -not -path "*/venv/*" \
      -not -path "*/env/*" \
      -not -path "*/.env/*" \
      -not -path "./nexus.txt" \
      -not -path "./book.md" \
      -not -path "./snapshot.txt" \
      -not -path "./temp_*" \
      -not -path "./available_models.json" \
      -not -path "*/.ruff_cache/*" \
      -not -path "./directives/*" \
      -not -path "./pipelines/*" \
      -not -path "./examples/*" \
      -not -path "./docs/*" \
      -not -path "./tests/*" \
      -not -path "./snapshot_chunks/*" \
      | sed 's/^\.\///' | sort > relevant_files.txt

    while IFS= read -r file; do
      if [ -n "$file" ]; then
        echo "=== FILE: $file ===" >> "$OUTPUT_FILE"
        cat "$file" >> "$OUTPUT_FILE"
        echo -e "\n\n" >> "$OUTPUT_FILE"
      fi
    done < relevant_files.txt

    # Clean up temporary files
    rm -f temp_tree_output.txt relevant_files.txt

    # If chunking is requested, split the file
    if [ "$CHUNK_OUTPUT" = true ]; then
        echo "Splitting snapshot into 100KB chunks with special message..."

        # Create output directory for chunks
        output_dir="snapshot_chunks"
        mkdir -p "$output_dir"

        # Split the file
        split -b ${CHUNK_SIZE} "$OUTPUT_FILE" "${output_dir}/snapshot_part_"

        # Add the special message to each chunk
        for file in "${output_dir}/snapshot_part_"*; do
            echo -e "\nSay \"received.\" after this message. DO nothing else." >> "$file"
        done

        # Report the result
        num_chunks=$(ls "$output_dir" | wc -l)
        echo "Snapshot has been split into $num_chunks chunk(s)."
        echo "Chunks are located in: $output_dir"
        for chunk in "$output_dir"/*; do
            chunk_name=$(basename "$chunk")
            # GNU stat; if you're on macOS, replace with: stat -f%z
            chunk_size=$(stat -c%s "$chunk" 2>/dev/null || stat -f%z "$chunk")
            echo " - $chunk_name ($chunk_size characters)"
        done
    else
        echo "Project snapshot created: $OUTPUT_FILE"
        echo "Snapshot includes:"
        echo "- Project structure tree"
        echo "- All relevant source code files"
        echo "- Configuration files"
        echo "- Documentation files"
        echo ""
        echo "Files excluded: books/, __pycache__, .git/, build/, dist/, node_modules/, available_models.json, snapshot_chunks/"
        echo ""
        echo "To create chunked output, run: ./snapshot.sh --chunk"
    fi
fi
