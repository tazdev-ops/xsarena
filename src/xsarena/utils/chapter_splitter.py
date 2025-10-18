"""Chapter splitting utilities for XSArena."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Chapter:
    """Represents a single chapter with content and metadata."""

    title: str
    content: str
    index: int
    prev_chapter: str = None
    next_chapter: str = None


def split_book_into_chapters(book_path: str, output_dir: str) -> List[Chapter]:
    """Split a book into chapters based on H1/H2 headings."""
    book_content = Path(book_path).read_text(encoding="utf-8")

    # Find all H1 and H2 headings with their positions
    headings = []
    h1_pattern = r"^(#{1,2})\s+(.+)$"

    for i, line in enumerate(book_content.split("\n")):
        match = re.match(h1_pattern, line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append(
                {
                    "line_num": i,
                    "level": level,
                    "title": title,
                    "pos": book_content.split("\n")[: i + 1],
                }
            )

    # Calculate positions more accurately
    lines = book_content.split("\n")
    heading_positions = []

    for i, line in enumerate(lines):
        match = re.match(h1_pattern, line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # Calculate the actual character position
            pos = 0
            for j in range(i):
                pos += len(lines[j]) + 1  # +1 for newline
            heading_positions.append(
                {"pos": pos, "end_pos": pos + len(line), "level": level, "title": title}
            )

    # Extract chapters
    chapters = []
    for i, heading in enumerate(heading_positions):
        start_pos = heading["pos"]
        end_pos = (
            heading_positions[i + 1]["pos"]
            if i + 1 < len(heading_positions)
            else len(book_content)
        )

        chapter_content = book_content[start_pos:end_pos]

        # Clean up content - remove the heading from the content since it's the title
        lines = chapter_content.split("\n")
        # Remove the first line which is the heading
        if lines and re.match(h1_pattern, lines[0].strip()):
            content_lines = lines[1:]  # Skip the heading line
        else:
            content_lines = lines

        # Join and clean up content
        clean_content = "\n".join(content_lines).strip()

        # Add navigation links
        prev_title = heading_positions[i - 1]["title"] if i > 0 else None
        next_title = (
            heading_positions[i + 1]["title"]
            if i < len(heading_positions) - 1
            else None
        )

        chapter = Chapter(
            title=heading["title"],
            content=clean_content,
            index=i,
            prev_chapter=prev_title,
            next_chapter=next_title,
        )
        chapters.append(chapter)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Write chapters to files
    for chapter in chapters:
        # Sanitize title for filename
        filename = (
            re.sub(r"[^\w\s-]", "", chapter.title).strip().replace(" ", "_").lower()
        )
        if not filename:
            filename = f"chapter_{chapter.index:02d}"

        filepath = Path(output_dir) / f"{filename}.md"

        # Add navigation links to content
        nav_content = []
        nav_content.append(f"# {chapter.title}\n")

        if chapter.prev_chapter:
            prev_filename = (
                re.sub(r"[^\w\s-]", "", chapter.prev_chapter)
                .strip()
                .replace(" ", "_")
                .lower()
            )
            if not prev_filename:
                prev_filename = f"chapter_{chapter.index-1:02d}"
            nav_content.append(f"[← {chapter.prev_chapter}]({prev_filename}.md) | ")

        nav_content.append("[Contents](toc.md)")

        if chapter.next_chapter:
            next_filename = (
                re.sub(r"[^\w\s-]", "", chapter.next_chapter)
                .strip()
                .replace(" ", "_")
                .lower()
            )
            if not next_filename:
                next_filename = f"chapter_{chapter.index+1:02d}"
            nav_content.append(f" | [Next: {chapter.next_chapter}]({next_filename}.md)")

        nav_content.append("\n\n")
        nav_content.append(chapter.content)

        Path(filepath).write_text("".join(nav_content), encoding="utf-8")

    # Create table of contents
    toc_content = ["# Table of Contents\n\n"]
    for i, chapter in enumerate(chapters):
        filename = (
            re.sub(r"[^\w\s-]", "", chapter.title).strip().replace(" ", "_").lower()
        )
        if not filename:
            filename = f"chapter_{i:02d}"
        toc_content.append(f"{i+1}. [{chapter.title}]({filename}.md)\n")

    toc_path = Path(output_dir) / "toc.md"
    Path(toc_path).write_text("".join(toc_content), encoding="utf-8")

    return chapters


def export_chapters(book_path: str, output_dir: str):
    """Export the book into chapters with navigation."""
    chapters = split_book_into_chapters(book_path, output_dir)
    return chapters
