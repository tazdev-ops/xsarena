"""Study and learning modes for XSArena."""

import asyncio
import re
from collections import Counter
from pathlib import Path

import typer

from ..modes.study import StudyMode
from .context import CLIContext

app = typer.Typer(help="Study and learning tools (flashcards, quizzes, etc.)")


def _read_content_file(file_path: str) -> str:
    p = Path(file_path)
    if not p.exists():
        typer.echo(f"Error: Content file not found at '{file_path}'")
        raise typer.Exit(1)
    return p.read_text(encoding="utf-8")


def _extract_terms_with_frequency(content: str) -> Counter:
    """Extract terms and their frequencies from content."""
    # Find potential terms: capitalized words, words in bold/italic, etc.
    # This is a simple heuristic - in a real implementation, you'd want more sophisticated NLP
    words = re.findall(r"\b[A-Z][a-z]+\b|\b[A-Z]{2,}\b", content)

    # Filter out common words that are unlikely to be terms
    common_words = {
        "The",
        "And",
        "For",
        "With",
        "From",
        "When",
        "Where",
        "Who",
        "What",
        "Why",
        "How",
        "This",
        "That",
        "These",
        "Those",
        "Is",
        "Are",
        "Was",
        "Were",
        "Be",
        "Been",
        "Being",
        "Have",
        "Has",
        "Had",
        "Do",
        "Does",
        "Did",
        "Will",
        "Would",
        "Could",
        "Should",
        "May",
        "Might",
    }

    filtered_words = [
        word for word in words if word not in common_words and len(word) > 2
    ]
    return Counter(filtered_words)


def _extract_headings(content: str, depth: int = 2) -> list:
    """Extract headings up to a certain depth."""
    headings = []
    lines = content.split("\n")

    for line in lines:
        # Match markdown headings: #, ##, ###, etc.
        header_match = re.match(r"^(\s*)(#{1," + str(depth) + r"})\s+(.+)$", line)
        if header_match:
            level = len(header_match.group(2))
            title = header_match.group(3).strip()
            headings.append({"level": level, "title": title})

    return headings


@app.command("flashcards")
def study_flashcards(
    ctx: typer.Context,
    content_file: str = typer.Argument(
        ..., help="Path to the content file to process."
    ),
    num_cards: int = typer.Option(
        50, "--num", "-n", help="Number of flashcards to generate."
    ),
):
    """Generate flashcards from a content file."""
    cli: CLIContext = ctx.obj
    study_mode = StudyMode(cli.engine)
    content = _read_content_file(content_file)
    result = asyncio.run(study_mode.generate_flashcards(content, num_cards))
    print(result)


@app.command("quiz")
def study_quiz(
    ctx: typer.Context,
    content_file: str = typer.Argument(
        ..., help="Path to the content file to process."
    ),
    num_questions: int = typer.Option(
        20, "--num", "-n", help="Number of questions to generate."
    ),
):
    """Generate a quiz from a content file."""
    cli: CLIContext = ctx.obj
    study_mode = StudyMode(cli.engine)
    content = _read_content_file(content_file)
    result = asyncio.run(study_mode.generate_quiz(content, num_questions))
    print(result)


@app.command("glossary")
def study_glossary(
    ctx: typer.Context,
    content_file: str = typer.Argument(
        ..., help="Path to the content file to process."
    ),
    min_occurs: int = typer.Option(
        2, "--min-occurs", help="Minimum occurrences for a term to be included"
    ),
    output_file: str = typer.Option(None, "--out", help="Output file for the glossary"),
):
    """Create a glossary from a content file with frequency filtering."""
    cli: CLIContext = ctx.obj
    StudyMode(cli.engine)
    content = _read_content_file(content_file)

    # Get terms with frequency
    term_counts = _extract_terms_with_frequency(content)

    # Filter by minimum occurrences
    filtered_terms = {
        term: count for term, count in term_counts.items() if count >= min_occurs
    }

    # Generate glossary with the filtered terms
    if filtered_terms:
        # Create a custom glossary based on frequent terms
        glossary_lines = ["# Glossary\n"]
        for term, count in sorted(filtered_terms.items()):
            glossary_lines.append(f"\n## {term}\n")
            glossary_lines.append(f"Frequency: {count} occurrences\n")

        result = "\n".join(glossary_lines)
    else:
        result = "# Glossary\n\nNo terms found with the specified minimum occurrence threshold."

    if output_file:
        Path(output_file).write_text(result, encoding="utf-8")
        typer.echo(f"Glossary saved to {output_file}")
    else:
        print(result)


@app.command("index")
def study_index(
    ctx: typer.Context,
    content_file: str = typer.Argument(
        ..., help="Path to the content file to process."
    ),
    depth: int = typer.Option(
        2, "--depth", help="Maximum heading depth to include (1-6)"
    ),
    output_file: str = typer.Option(None, "--out", help="Output file for the index"),
):
    """Generate an index from a content file with depth control."""
    cli: CLIContext = ctx.obj
    StudyMode(cli.engine)
    content = _read_content_file(content_file)

    # Extract headings up to the specified depth
    headings = _extract_headings(content, depth)

    # Generate index
    if headings:
        index_lines = ["# Index\n"]

        for heading in headings:
            indent = "  " * (heading["level"] - 1)
            index_lines.append(f"{indent}- {heading['title']}")

        result = "\n".join(index_lines)
    else:
        result = "# Index\n\nNo headings found in the content."

    if output_file:
        Path(output_file).write_text(result, encoding="utf-8")
        typer.echo(f"Index saved to {output_file}")
    else:
        print(result)
