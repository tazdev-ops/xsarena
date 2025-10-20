#!/usr/bin/env python3
"""
EPUB Translation Tool for XSArena

This script automates the process of translating an EPUB book using XSArena's
bilingual mode while preserving formatting and structure.

Usage:
    python epub_translate.py input.epub --source English --target Spanish

For more options:
    python epub_translate.py --help
"""
import argparse
import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import xsarena modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xsarena.cli.context import CLIContext
from xsarena.modes.bilingual import BilingualMode


def check_prerequisites():
    """Check if required tools are available."""
    try:
        # Check if pandoc is available
        subprocess.run(["pandoc", "--version"], capture_output=True, check=True)
        print("✓ pandoc is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ pandoc not found. Install it for EPUB conversion.")
        print("  Ubuntu/Debian: sudo apt install pandoc")
        print("  macOS: brew install pandoc")
        print("  Windows: choco install pandoc")
        return False

    return True


def epub_to_markdown(epub_path, output_path, wrap="none"):
    """Convert EPUB to Markdown using pandoc."""
    cmd = ["pandoc", str(epub_path), "-t", "markdown", "-o", str(output_path)]

    if wrap == "none":
        cmd.extend(["--wrap=none"])

    print(f"Converting EPUB to Markdown: {epub_path} → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error converting EPUB: {result.stderr}")
        return False

    return True


def split_chapters(markdown_path, output_dir):
    """Split markdown file into chapters using XSArena's export-chapters tool."""
    print(f"Splitting into chapters: {markdown_path} → {output_dir}")

    # Use XSArena's export-chapters tool
    cmd = [
        sys.executable,
        "-m",
        "xsarena",
        "utils",
        "tools",
        "export-chapters",
        str(markdown_path),
        "--out",
        str(output_dir),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error splitting chapters: {result.stderr}")
        return False

    return True


def translate_chapters(
    input_dir, output_dir, source_lang, target_lang, chunk_size=9000
):
    """Translate all chapters in the input directory."""
    # Translation policy guidance
    extra_policy = f"""Translation policy:
- Preserve all Markdown structure (headings, lists, tables).
- Do not translate code blocks (```), inline code (`code`), URLs, or image filenames.
- Keep link anchors and references intact.
- Translate headings, body, and alt text. Maintain list/numbering.
- Preserve emphasis (*italic*, **bold**) and other Markdown formatting.
- Target language: {target_lang}
"""

    print(f"Translating chapters from '{input_dir}' to '{output_dir}'")
    print(f"Language pair: {source_lang} → {target_lang}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load XSArena context and mode
    try:
        ctx = CLIContext.load()
        mode = BilingualMode(ctx.engine)
    except Exception as e:
        print(f"Error loading XSArena context: {e}")
        print("Make sure XSArena is properly configured and the bridge is running.")
        return False

    # Get all markdown files
    paths = sorted(input_dir.glob("*.md"))

    if not paths:
        print(f"No markdown files found in {input_dir}")
        return False

    print(f"Found {len(paths)} chapters to translate")

    for i, path in enumerate(paths, 1):
        print(f"Processing [{i}/{len(paths)}]: {path.name}")

        # Read the chapter content
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Error reading file {path}: {e}")
            continue

        # Chunk very large files to avoid token limits
        chunks = []
        remaining = text
        while remaining:
            chunks.append(remaining[:chunk_size])
            remaining = remaining[chunk_size:]

        # Translate each chunk
        translated_parts = []
        for j, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"  Chunk {j}/{len(chunks)}")

            try:
                # Translate the chunk
                translated_text = asyncio.run(
                    mode.transform(chunk, source_lang, target_lang, extra_policy)
                )
                translated_parts.append(translated_text)
            except Exception as e:
                print(f"  Error translating chunk {j}: {e}")
                # If translation fails, keep the original text
                translated_parts.append(chunk)

        # Write the complete translated chapter
        out_path = output_dir / path.name
        try:
            out_path.write_text("".join(translated_parts), encoding="utf-8")
            print(f"  ✓ Saved to {out_path}")
        except Exception as e:
            print(f"  Error writing file {out_path}: {e}")
            continue

    print("Translation complete!")
    return True


def rebuild_epub(input_dir, output_path, title=None):
    """Rebuild EPUB from translated markdown files."""
    print(f"Rebuilding EPUB: {input_dir}/*.md → {output_path}")

    # Get all markdown files in order
    md_files = sorted(input_dir.glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return False

    # Build pandoc command
    cmd = ["pandoc"]

    # Add all markdown files
    cmd.extend([str(f) for f in md_files])

    # Set output format
    cmd.extend(["-o", str(output_path)])

    # Add title if provided
    if title:
        cmd.extend(["--metadata", f"title={title}"])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error rebuilding EPUB: {result.stderr}")
        return False

    print(f"✓ EPUB rebuilt: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Translate an EPUB book using XSArena's bilingual mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.epub --source English --target Spanish
  %(prog)s input.epub --source English --target French --output my_book.epub
  %(prog)s input.epub --source English --target Spanish --chunk-size 7000
        """,
    )

    parser.add_argument("input", help="Input EPUB file to translate")
    parser.add_argument(
        "--source", default="English", help="Source language (default: English)"
    )
    parser.add_argument("--target", required=True, help="Target language")
    parser.add_argument(
        "--output", "-o", help="Output EPUB file (default: input_translated.epub)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=9000,
        help="Maximum characters per translation chunk (default: 9000)",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Skip chapter splitting (if input is already split)",
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Skip EPUB rebuilding (only translate chapters)",
    )
    parser.add_argument("--work-dir", help="Working directory for temporary files")

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return 1

    if input_path.suffix.lower() != ".epub":
        print(f"Warning: Input file doesn't have .epub extension: {input_path}")

    # Set up working directory
    work_dir = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp())
    print(f"Using working directory: {work_dir}")

    # Set up other directories
    markdown_file = work_dir / "book.md"
    chapters_dir = work_dir / "chapters"
    translated_dir = work_dir / "translated"

    # Set up output file
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(
            input_path.stem + f"_translated_{args.target.lower()}.epub"
        )

    # Check prerequisites
    if not check_prerequisites():
        print("Prerequisites not met. Please install required tools.")
        return 1

    # Step 1: Convert EPUB to Markdown
    print("\n=== Step 1: Converting EPUB to Markdown ===")
    if not epub_to_markdown(input_path, markdown_file):
        print("Failed to convert EPUB to Markdown")
        return 1

    # Step 2: Split into chapters (unless --no-split is specified)
    if not args.no_split:
        print("\n=== Step 2: Splitting into chapters ===")
        if not split_chapters(markdown_file, chapters_dir):
            print("Failed to split chapters")
            return 1
    else:
        # If no split, treat the whole markdown file as one chapter
        chapters_dir.mkdir(exist_ok=True)
        (chapters_dir / "full_book.md").write_text(markdown_file.read_text())

    # Step 3: Translate chapters
    print("\n=== Step 3: Translating chapters ===")
    if not translate_chapters(
        chapters_dir, translated_dir, args.source, args.target, args.chunk_size
    ):
        print("Failed to translate chapters")
        return 1

    # Step 4: Rebuild EPUB (unless --no-rebuild is specified)
    if not args.no_rebuild:
        print("\n=== Step 4: Rebuilding EPUB ===")
        title = f"{input_path.stem} ({args.target})"
        if not rebuild_epub(translated_dir, output_path, title):
            print("Failed to rebuild EPUB")
            return 1

        print(f"\n✓ Translation complete! Output: {output_path}")
    else:
        print(f"\n✓ Translation complete! Translated files in: {translated_dir}")
        print(f"  To rebuild manually: pandoc {translated_dir}/*.md -o output.epub")

    return 0


if __name__ == "__main__":
    sys.exit(main())
