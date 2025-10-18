"""Analysis commands for XSArena."""

from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Analysis, reporting, and evidence-based tools.")

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
    path: str = typer.Argument(
        ".", help="Path to scan for secrets (defaults to current directory)"
    ),
    no_fail: bool = typer.Option(
        False, "--no-fail", help="Don't exit with error code if secrets are found"
    ),
):
    """Scan for secrets (API keys, passwords, etc.) in the specified path."""
    from ..utils.secrets_scanner import scan_secrets

    typer.echo(f"Scanning '{path}' for potential secrets...")

    findings, has_secrets = scan_secrets(path, fail_on_hits=not no_fail)

    if has_secrets:
        if not no_fail:
            typer.echo("\\nSecrets found! Exiting with error code.", err=True)
            raise typer.Exit(code=1)
        else:
            typer.echo("\\nSecrets found, but continuing as --no-fail was specified.")
    else:
        typer.echo("\\nNo secrets found. Scan completed successfully.")
