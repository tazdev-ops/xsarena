#!/bin/bash
# Generate books from topic list

if [ ! -f topics.txt ]; then
    echo "Error: topics.txt not found"
    exit 1
fi

mkdir -p ./books/batch

while IFS= read -r topic; do
    [ -z "$topic" ] && continue  # Skip empty lines

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Generating: $topic"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    filename=$(echo "$topic" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    xsarena run book "$topic" \
        --length long \
        --span medium \
        --out "./books/batch/${filename}.md" \
        --follow

    echo "✓ Completed: $topic"
    echo ""
done < topics.txt

echo "All books generated!"
