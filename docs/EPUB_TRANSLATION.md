# EPUB Translation with XSArena

This guide explains how to translate an EPUB book using XSArena's bilingual mode while preserving formatting and structure.

## Overview

The translation process involves:
1. Converting the EPUB to Markdown
2. Splitting into chapters
3. Translating each chapter using XSArena's bilingual mode
4. Rebuilding the EPUB from translated chapters

This approach preserves formatting, links, code blocks, and other structural elements while enabling AI-powered translation.

## Prerequisites

Before starting, ensure you have:

- **Firefox** with **Tampermonkey** extension installed
- XSArena bridge userscript installed and active in Tampermonkey
- Bridge server running locally: `xsarena ops service start-bridge-v2`
- LMArena tab open with `#bridge=5102` parameter (or your custom port)
- `pandoc` installed for EPUB conversion (recommended)
- The source EPUB file ready

## Step-by-Step Process

### 1. Convert EPUB to Markdown

Choose one of these methods to convert your EPUB to Markdown:

**Using Pandoc (recommended):**
```bash
pandoc "input.epub" -t markdown -o book.md --wrap=none
```

**Using Calibre:**
```bash
ebook-convert "input.epub" book.md
```

> **Tip:** Use `--wrap=none` with pandoc to avoid hard-wrapped lines that can confuse translation.

### 2. Split into Chapters

Use XSArena's built-in chapter exporter to split the large Markdown file into manageable chapters:

```bash
xsarena utils tools export-chapters book.md --out ./chapters
```

This creates `./chapters/*.md` files and a `toc.md` table of contents.

### 3. Translation Policy

For best results, ensure the translator preserves:
- All Markdown structure (headings, lists, tables)
- Code blocks (```) and inline code (`code`)
- URLs and image filenames
- Link anchors and references
- Translates headings, body text, and alt text

### 4. Translate Chapters

#### Option A: Python Helper Script (Recommended)

For reliable translation without shell argument limits, create a Python script:

```python
#!/usr/bin/env python3
"""
EPUB Translation Helper
Translates chapters from an EPUB while preserving Markdown structure.
"""
import os
import glob
import asyncio
from pathlib import Path

from xsarena.cli.context import CLIContext
from xsarena.modes.bilingual import BilingualMode

# Configuration
SOURCE_LANG = "English"
TARGET_LANG = "Spanish"  # Change to your target language
IN_DIR = Path("chapters")
OUT_DIR = Path("translated")
CHUNK_SIZE = 9000  # Characters to chunk large files (to avoid token limits)

# Translation policy guidance
EXTRA_POLICY = """Translation policy:
- Preserve all Markdown structure (headings, lists, tables).
- Do not translate code blocks (```), inline code (`code`), URLs, or image filenames.
- Keep link anchors and references intact.
- Translate headings, body, and alt text. Maintain list/numbering.
- Preserve emphasis (*italic*, **bold**) and other Markdown formatting.
"""

def main():
    # Create output directory
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load XSArena context and mode
    ctx = CLIContext.load()
    mode = BilingualMode(ctx.engine)

    # Get all chapter files
    paths = sorted(IN_DIR.glob("*.md"))

    print(f"Found {len(paths)} chapters to translate")

    for i, path in enumerate(paths, 1):
        print(f"Processing [{i}/{len(paths)}]: {path.name}")

        # Read the chapter content
        text = path.read_text(encoding="utf-8")

        # Chunk very large files to avoid token limits
        chunks = []
        remaining = text
        while remaining:
            chunks.append(remaining[:CHUNK_SIZE])
            remaining = remaining[CHUNK_SIZE:]

        # Translate each chunk
        translated_parts = []
        for j, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"  Chunk {j}/{len(chunks)}")

            # Translate the chunk
            translated_text = asyncio.run(
                mode.transform(chunk, SOURCE_LANG, TARGET_LANG, EXTRA_POLICY)
            )
            translated_parts.append(translated_text)

        # Write the complete translated chapter
        out_path = OUT_DIR / path.name
        out_path.write_text("".join(translated_parts), encoding="utf-8")
        print(f"  ✓ Saved to {out_path}")

    print("Translation complete!")

if __name__ == "__main__":
    main()
```

Save this as `translate_epub.py` and run it:

```bash
python translate_epub.py
```

#### Option B: Simple CLI Loop (For small chapters)

For smaller chapters, you can use a simple bash loop:

```bash
mkdir -p translated
for f in chapters/*.md; do
  echo "Translating: $(basename "$f")"
  xsarena bilingual transform "$(cat "$f")" --source English --target Spanish > "translated/$(basename "$f")"
done
```

> **Note:** If you encounter "argument list too long" errors, use the Python helper instead.

### 5. Quality Assurance (Optional)

#### Create a Glossary for Consistency

Generate a glossary to ensure consistent translation of key terms:

```bash
xsarena bilingual glossary chapters/01_*.md --source English --target Spanish > glossary.md
```

#### Check Alignment

Verify alignment between source and translated chapters:

```bash
xsarena bilingual check chapters/01_intro.md translated/01_intro.md --source English --target Spanish
```

#### Improve Problematic Chapters

Improve chapters that didn't translate well:

```bash
xsarena bilingual improve chapters/05_topic.md translated/05_topic.md --source English --target Spanish > translated/05_topic.improved.md
```

### 6. Rebuild EPUB

Once all chapters are translated and verified, rebuild the EPUB:

```bash
pandoc translated/*.md -o output-translated.epub --metadata title="Your Book (Translated)"
```

You can add additional metadata or cover images using pandoc's various options.

## Tips and Gotchas

### Bridge Setup
- Keep the Firefox tab open with `#bridge=5102` (or your port) so the userscript stays connected
- Watch the bridge logs for "Userscript connected" status
- If you have internal token gating enabled, translation calls through `/v1/chat/completions` don't require the token

### Handling Large Files
- Chunking at ~9-10k characters is a good default to avoid token limits
- Adjust chunk size based on content density (smaller for code-heavy content)

### Preserving Structure
- The EXTRA_POLICY helps guide the translator to preserve code blocks
- Explicitly mention "Don't translate inside ``` blocks or `inline` code" in the policy
- Links and images: Keep URLs/filenames unchanged, translate alt text

### Performance
- Sequential processing keeps things simple
- For speed, you can parallelize with asyncio.gather, but monitor the bridge to avoid overloading

## Quick Smoke Test

To verify everything works:

1. Take one small chapter
2. Run the transform for English→Spanish
3. Open the translated MD to ensure headings/lists/code fences look intact
4. Build a tiny EPUB from 1-2 translated chapters to verify formatting

## Troubleshooting

### Bridge Connection Issues
- Ensure Firefox has the userscript installed and enabled
- Verify the LMArena tab has the correct `#bridge=PORT` parameter
- Check that the bridge server is running on the expected port

### Token Limits
- If getting token limit errors, reduce the CHUNK_SIZE in the Python script
- Large chapters may need to be manually split before translation

### Formatting Issues
- If Markdown structure is not preserved, ensure the EXTRA_POLICY is being passed correctly
- Some translators may need explicit instructions about code blocks and links

---

This workflow leverages XSArena's bilingual mode while preserving formatting through the Markdown format, and the final build back to EPUB is a single pandoc command.
