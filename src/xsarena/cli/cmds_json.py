"""CLI commands for JSON validation and processing."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from jsonschema import ValidationError, validate

from .context import CLIContext

app = typer.Typer(help="JSON validation and processing tools")


@app.command("validate")
def json_validate(
    file_path: str = typer.Argument(
        ..., help="JSON file to validate (use '-' for stdin)"
    ),
    schema_path: str = typer.Option(
        ..., "--schema", help="Schema file to validate against"
    ),
):
    """Validate JSON file against a schema."""
    # Read JSON content
    if file_path == "-":
        content = sys.stdin.read()
        data = json.loads(content)
    else:
        file_p = Path(file_path)
        if not file_p.exists():
            typer.echo(f"Error: File '{file_path}' does not exist", err=True)
            raise typer.Exit(code=1)
        try:
            data = json.loads(file_p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            typer.echo(f"Error: Invalid JSON in '{file_path}': {e}", err=True)
            raise typer.Exit(code=1)

    # Read schema
    schema_p = Path(schema_path)
    if not schema_p.exists():
        typer.echo(f"Error: Schema file '{schema_path}' does not exist", err=True)
        raise typer.Exit(code=1)

    try:
        schema = json.loads(schema_p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON in schema '{schema_path}': {e}", err=True)
        raise typer.Exit(code=1)

    # Validate
    try:
        validate(instance=data, schema=schema)
        typer.echo("✓ JSON is valid against the schema")
        raise typer.Exit(code=0)
    except ValidationError as e:
        typer.echo(f"✗ JSON validation failed: {e.message}", err=True)
        # Print more specific path information
        if e.absolute_path:
            path_str = " -> ".join([str(p) for p in e.absolute_path])
            typer.echo(f"  at path: {path_str}", err=True)
        raise typer.Exit(code=1)


@app.command("lint-template")
def lint_template(file_path: str = typer.Argument(..., help="Template file to lint")):
    """Lint a prompt template file for JSON schema compliance."""
    file_p = Path(file_path)
    if not file_p.exists():
        typer.echo(f"Error: File '{file_path}' does not exist", err=True)
        raise typer.Exit(code=1)

    content = file_p.read_text(encoding="utf-8")

    # Check if the content contains a JSON block with keys/types or schema
    has_schema_reference = False

    # Look for JSON code blocks with schema information
    import re

    json_blocks = re.findall(
        r"```json\s*\n(.*?)\n```", content, re.DOTALL | re.IGNORECASE
    )

    for block in json_blocks:
        try:
            json_data = json.loads(block)
            # Check if it looks like a schema or has type information
            if isinstance(json_data, dict) and (
                "type" in json_data
                or "properties" in json_data
                or "$schema" in json_data
            ):
                has_schema_reference = True
        except json.JSONDecodeError:
            # If it's not valid JSON, continue checking other patterns
            continue

    # Look for references to schema in comments or text
    if "schema" in content.lower() or "json" in content.lower():
        has_schema_reference = True

    # Check for malformed JSON structures
    try:
        # Try to find and validate any JSON in the content
        json_candidates = re.findall(
            r"\{[^{}]*\}", content
        )  # Simple JSON object detection
        for candidate in json_candidates:
            try:
                json.loads(candidate)
            except json.JSONDecodeError:
                # This might be a malformed JSON snippet
                pass
    except re.error:
        pass

    # Output results
    if has_schema_reference:
        typer.echo("✓ Template contains JSON schema or type information")
        raise typer.Exit(code=0)
    else:
        typer.echo(
            "⚠ Template does not contain obvious JSON schema or type information",
            err=True,
        )
        typer.echo(
            "  Consider adding a JSON schema block or type definitions for validation",
            err=True,
        )
        # Return 0 for warnings but non-zero for actual errors
        raise typer.Exit(code=0)  # Linting is for warnings, not hard failures


@app.command("run")
def json_run(
    ctx: typer.Context,
    system: str = typer.Option(
        "", "--system", "-s", help="System prompt text or path to a file"
    ),
    text: str = typer.Option(
        "", "--text", "-t", help="User text (ignored if --file provided)"
    ),
    file: str = typer.Option(
        "", "--file", "-f", help="Path to user text file (takes precedence over --text)"
    ),
    out: str = typer.Option(
        "", "--out", "-o", help="Write output to file (stdout if empty)"
    ),
    validate_schema: Optional[str] = typer.Option(
        None, "--validate", help="Schema file to validate JSON output against"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Fail if validation fails (otherwise just report)"
    ),
):
    """Run a prompt and optionally validate JSON output against a schema."""

    def _read_maybe_path(s: str) -> str:
        p = Path(s)
        return p.read_text(encoding="utf-8") if p.exists() and p.is_file() else s

    cli: CLIContext = ctx.obj
    system_prompt = (
        _read_maybe_path(system) if system else "You are a helpful assistant."
    )
    user_body = (
        Path(file).read_text(encoding="utf-8")
        if file and Path(file).exists()
        else (text or typer.prompt("Enter prompt text"))
    )

    try:
        result = asyncio.run(
            cli.engine.send_and_collect(user_body, system_prompt=system_prompt)
        )
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # If output file specified, write to file
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(result, encoding="utf-8")
        typer.echo(f"→ {out}")
    else:
        typer.echo(result)

    # If validation schema provided, validate the output
    if validate_schema:
        schema_p = Path(validate_schema)
        if not schema_p.exists():
            typer.echo(
                f"Error: Schema file '{validate_schema}' does not exist", err=True
            )
            raise typer.Exit(code=1)

        try:
            schema = json.loads(schema_p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            typer.echo(
                f"Error: Invalid JSON in schema '{validate_schema}': {e}", err=True
            )
            raise typer.Exit(code=1)

        # Try to parse the result as JSON for validation
        try:
            # Extract JSON from result if it's in a code block
            import re

            json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", result, re.DOTALL)
            json_content = json_match.group(1) if json_match else result

            data = json.loads(json_content)
            validate(instance=data, schema=schema)
            typer.echo("Schema: OK")
        except json.JSONDecodeError:
            typer.echo("Schema: Not valid JSON", err=True)
            if strict:
                raise typer.Exit(code=1)
        except ValidationError as e:
            typer.echo(f"Schema: Validation failed - {e.message}", err=True)
            if strict:
                raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Schema: Error during validation - {e}", err=True)
            if strict:
                raise typer.Exit(code=1)
