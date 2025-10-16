from __future__ import annotations

import subprocess
from pathlib import Path

import typer

app = typer.Typer(help="Checklist and verification commands for XSArena implementation")


@app.command("status")
def checklist_status():
    """Run the implementation checklist and report status."""
    typer.echo("=== XSArena Implementation Checklist Status ===")

    # Define checks to run
    checks = [
        ("Health: xsarena fix run", lambda: run_command("xsarena fix run")),
        ("Health: xsarena backend test", lambda: run_command("xsarena backend test")),
        ("Adapt: xsarena adapt inspect", lambda: run_adapt_inspect()),
        ("Clean: xsarena clean sweep", lambda: run_command("xsarena clean sweep")),
        ("Snapshot: xsarena snapshot write", lambda: run_snapshot_write()),
        ("Report: xsarena report quick", lambda: run_report_quick()),
        ("Boot: xsarena boot read", lambda: run_command("xsarena boot read")),
        ("Help: xsarena --help", lambda: run_command("xsarena --help")),
        ("Main config file", lambda: check_file(".xsarena/config.yml")),
        ("Merged rules", lambda: check_file("directives/_rules/rules.merged.md")),
        (
            "CLI agent rules",
            lambda: check_file("directives/_rules/sources/CLI_AGENT_RULES.md"),
        ),
        ("Startup config", lambda: check_file(".xsarena/ops/startup.yml")),
        ("ROADMAP.md", lambda: check_file("ROADMAP.md")),
        ("SUPPORT.md", lambda: check_file("SUPPORT.md")),
        ("CONFIG_REFERENCE.md", lambda: check_file("CONFIG_REFERENCE.md")),
        ("MODULES.md", lambda: check_file("MODULES.md")),
        ("CHANGELOG.md", lambda: check_file("CHANGELOG.md")),
        ("STATE.md", lambda: check_file("docs/STATE.md")),
        ("GIT_POLICY.md", lambda: check_file("docs/GIT_POLICY.md")),
        ("Merge script", lambda: check_file("scripts/merge_session_rules.sh")),
        ("Prepush script", lambda: check_file("scripts/prepush_check.sh")),
        (
            "Optimized snapshot tool",
            lambda: check_file("tools/minimal_snapshot_optimized.py"),
        ),
        ("Snapshot chunk tool", lambda: check_file("tools/snapshot_chunk.py")),
        ("Legacy chunk script", lambda: check_file("legacy/chunk_snapshot.sh")),
        ("PR template", lambda: check_file(".github/PULL_REQUEST_TEMPLATE.md")),
        ("Issue template", lambda: check_file(".github/ISSUE_TEMPLATE/bug_report.yml")),
    ]

    results = []
    for name, check_func in checks:
        try:
            success, message = check_func()
            status = "✅" if success else "❌"
            results.append((name, success))
            typer.echo(f"{status} {name} - {message}")
        except Exception as e:
            results.append((name, False))
            typer.echo(f"❌ {name} - Error: {str(e)}")

    # Summary
    total = len(results)
    passed = sum(1 for _, success in results if success)
    typer.echo(f"\n=== Summary: {passed}/{total} checks passed ===")

    if passed < total:
        typer.echo(f"⚠️  {total - passed} items need attention")
        typer.echo("Run 'xsarena checklist details' for more information")
    else:
        typer.echo("🎉 All checks passed!")


def run_command(cmd: str) -> tuple[bool, str]:
    """Run a command and return (success, message)."""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
        success = result.returncode == 0
        message = "OK" if success else f"Error: {result.stderr[:100]}..."
        return success, message
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def run_adapt_inspect() -> tuple[bool, str]:
    """Run adapt inspect and check for output file."""
    try:
        result = subprocess.run(
            ["xsarena", "adapt", "inspect"], capture_output=True, text=True, timeout=10
        )
        # Check if a review/adapt_plan_*.json file was created
        import glob

        files = glob.glob("review/adapt_plan_*.json")
        success = len(files) > 0
        message = (
            f"OK - {len(files)} plan(s) created"
            if success
            else f"Error: {result.stderr[:100]}..."
        )
        return success, message
    except Exception as e:
        return False, str(e)


def run_snapshot_write() -> tuple[bool, str]:
    """Run snapshot write and check for output file."""
    try:
        # Don't actually write the full snapshot, just check command exists
        result = subprocess.run(
            ["xsarena", "snapshot", "write"], capture_output=True, text=True, timeout=10
        )
        # Check if file exists in home directory
        snapshot_path = Path.home() / "xsa_min_snapshot.txt"
        success = snapshot_path.exists()
        message = (
            f"OK - File size: {snapshot_path.stat().st_size if success else 0} bytes"
            if success
            else f"Error: {result.stderr[:100]}..."
        )
        return success, message
    except Exception as e:
        return False, str(e)


def run_report_quick() -> tuple[bool, str]:
    """Run report quick and check for output file."""
    try:
        result = subprocess.run(
            ["xsarena", "report", "quick"], capture_output=True, text=True, timeout=15
        )
        # Check if a review/report_*.tar.gz file was created
        import glob

        files = glob.glob("review/report_*.tar.gz")
        success = len(files) > 0
        message = (
            f"OK - {len(files)} bundle(s) created"
            if success
            else f"Error: {result.stderr[:100]}..."
        )
        return success, message
    except Exception as e:
        return False, str(e)


def check_file(path: str) -> tuple[bool, str]:
    """Check if a file exists."""
    exists = Path(path).exists()
    return exists, "Exists" if exists else "Missing"


@app.command("details")
def checklist_details():
    """Show detailed checklist with specific verification commands."""
    typer.echo("=== Detailed Checklist with Verification Commands ===")
    typer.echo("Run these commands manually to verify each item:")
    typer.echo("")

    details = [
        ("xsarena fix run", "Check system health"),
        ("xsarena backend test", "Check backend connectivity"),
        ("xsarena adapt inspect", "Generate adaptation plan"),
        ("xsarena clean sweep", "List cleanup candidates"),
        ("xsarena snapshot write", "Create snapshot in home dir"),
        ("xsarena report quick", "Create report bundle"),
        ("xsarena boot read", "Read startup plan"),
        ("ls -la .xsarena/", "Check config directory"),
        ("ls -la directives/_rules/", "Check rules directory"),
        ("cat docs/IMPLEMENTATION_CHECKLIST.md", "View full checklist"),
    ]

    for cmd, desc in details:
        typer.echo(f"$ {cmd}")
        typer.echo(f"  # {desc}")
        typer.echo("")
