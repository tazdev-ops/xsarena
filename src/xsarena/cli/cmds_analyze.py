"""Analysis commands for XSArena."""

from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Analysis, reporting, and evidence-based tools.")

from ..utils.continuity import (
    analyze_continuity,
    generate_continuity_report,
    save_continuity_report,
)
from ..utils.coverage import (
    analyze_coverage,
    generate_coverage_report,
    save_coverage_report,
)
from ..utils.style_lint import lint_directive_file

console = Console()


@app.command("style-lint")
def style_lint_cmd(
    paths: List[Path] = typer.Argument(
        ...,
        help="Paths to directive files or directories to lint.",
        exists=True,
        readable=True,
    ),
):
    """Lint directive files for style, structure, and best practices."""
    console.print(f"[bold cyan]Linting {len(paths)} path(s)...[/bold cyan]")
    total_issues = 0

    files_to_lint = []
    for path in paths:
        if path.is_dir():
            files_to_lint.extend(p for p in path.rglob("*.md") if p.is_file())
        elif path.is_file():
            files_to_lint.append(path)

    for file_path in sorted(files_to_lint):
        issues = lint_directive_file(file_path)
        if issues:
            total_issues += len(issues)
            console.print(f"\n[yellow]File:[/yellow] {file_path}")
            table = Table("Line", "Code", "Message")
            for issue in issues:
                table.add_row(issue["line"], issue["code"], issue["message"])
            console.print(table)

    if total_issues == 0:
        console.print("\n[bold green]✓ No issues found.[/bold green]")
    else:
        console.print(f"\n[bold red]Found {total_issues} issue(s).[/bold red]")
        raise typer.Exit(code=1)


@app.command("coverage")
def coverage_cmd(
    outline: str = typer.Option(..., "--outline", help="Path to the outline file"),
    book: str = typer.Option(..., "--book", help="Path to the book file"),
    output: str = typer.Option(
        "review/coverage_report.md", "--output", "-o", help="Output path for the report"
    ),
):
    """Analyze coverage of a book against an outline."""
    # Verify files exist
    outline_path = Path(outline)
    book_path = Path(book)

    if not outline_path.exists():
        typer.echo(f"Error: Outline file not found at '{outline}'")
        raise typer.Exit(1)

    if not book_path.exists():
        typer.echo(f"Error: Book file not found at '{book}'")
        raise typer.Exit(1)

    # Perform coverage analysis
    typer.echo("Analyzing coverage...")
    coverage_items = analyze_coverage(str(outline_path), str(book_path))

    # Generate report
    report = generate_coverage_report(coverage_items, outline, book)

    # Save report
    save_coverage_report(report, output)

    # Also save JSON sidecar
    import json
    from dataclasses import asdict

    json_data = {
        "outline": outline,
        "book": book,
        "coverage_items": [asdict(item) for item in coverage_items],
        "summary": {
            "total": len(coverage_items),
            "covered": sum(1 for item in coverage_items if item.status == "Covered"),
            "partial": sum(1 for item in coverage_items if item.status == "Partial"),
            "missing": sum(1 for item in coverage_items if item.status == "Missing"),
        },
    }

    json_output = output.replace(".md", ".json")
    Path(json_output).write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    typer.echo("Coverage analysis complete!")
    typer.echo(f"Report saved to: {output}")
    typer.echo(f"JSON sidecar saved to: {json_output}")


@app.command("secrets")
def secrets_cmd(
    ctx: typer.Context,
    path: str = typer.Argument(
        ".", help="Path to scan for secrets (defaults to current directory)"
    ),
    no_fail: bool = typer.Option(
        False, "--no-fail", help="Don't exit with error code if secrets are found"
    ),
):
    """Scan for secrets (API keys, passwords, etc.) in the specified path."""
    # Print deprecation message
    typer.echo(
        "⚠️  DEPRECATION WARNING: 'xsarena analyze secrets' is deprecated. Use 'xsarena ops health scan-secrets' instead.",
        err=True,
    )

    # Import the health app and call the scan_secrets command via ctx.invoke
    from .cmds_health import scan_secrets as health_scan_secrets

    ctx.invoke(health_scan_secrets, path=path, no_fail=no_fail)


@app.command("continuity")
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


@app.command("readtime")
def readtime_cmd(
    file: Path = typer.Argument(..., help="Path to the text file to analyze"),
    words_per_minute: int = typer.Option(
        200, "--wpm", help="Words per minute reading speed"
    ),
):
    """Analyze reading time and density of a text file."""
    if not file.exists():
        typer.echo(f"Error: File '{file}' not found.", err=True)
        raise typer.Exit(1)

    content = file.read_text(encoding="utf-8")

    # Count words
    words = len(content.split())

    # Calculate reading time
    reading_time = words / words_per_minute

    # Calculate density (words per character)
    density = words / len(content) if len(content) > 0 else 0

    # Estimate reading time in minutes and seconds
    minutes = int(reading_time)
    seconds = int((reading_time - minutes) * 60)

    typer.echo(f"File: {file}")
    typer.echo(f"Words: {words:,}")
    typer.echo(f"Characters: {len(content):,}")
    typer.echo(f"Reading time: ~{minutes}m {seconds}s (at {words_per_minute} wpm)")
    typer.echo(
        f"Density: {density:.4f} words per character ({density*1000:.2f} words per 1000 characters)"
    )

    # Density interpretation
    if density > 0.15:
        typer.echo("Density: High (dense text)")
    elif density > 0.10:
        typer.echo("Density: Medium")
    else:
        typer.echo("Density: Low (sparse text)")
