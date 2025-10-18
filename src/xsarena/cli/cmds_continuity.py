"""Continuity analysis commands for XSArena."""

from pathlib import Path

import typer

from ..utils.continuity import (
    analyze_continuity,
    generate_continuity_report,
    save_continuity_report,
)


def continuity_cmd(
    book: str = typer.Argument(..., help="Path to the book file to analyze"),
    output: str = typer.Option(
        "review/continuity_report.md",
        "--output",
        "-o",
        help="Output path for the report",
    ),
):
    """Analyze book continuity for anchor drift and re-introductions."""
    # Verify file exists
    book_path = Path(book)

    if not book_path.exists():
        typer.echo(f"Error: Book file not found at '{book}'")
        raise typer.Exit(1)

    # Perform continuity analysis
    typer.echo("Analyzing continuity...")
    issues = analyze_continuity(str(book_path))

    # Generate report
    report = generate_continuity_report(issues, book)

    # Save report
    save_continuity_report(report, output)

    typer.echo("Continuity analysis complete!")
    typer.echo(f"Report saved to: {output}")

    # Print summary
    issue_counts = {}
    for issue in issues:
        issue_counts[issue.type] = issue_counts.get(issue.type, 0) + 1

    if issue_counts:
        typer.echo("Issues found:")
        for issue_type, count in issue_counts.items():
            typer.echo(f"  - {issue_type.title()}: {count}")
    else:
        typer.echo("No continuity issues detected!")
