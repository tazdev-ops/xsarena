"""Documentation and snapshot commands for XSArena project management."""

import json
import platform
import subprocess
import time
from pathlib import Path

import typer

app = typer.Typer(help="Documentation and snapshot commands")


@app.command("docs-regen")
def docs_regen():
    """Regenerate documentation (help files, etc.)."""
    typer.echo("Regenerating documentation...")

    try:
        # Try to run the shell script if it exists
        gen_script = Path("scripts/gen_docs.sh")
        if gen_script.exists():
            # Check if we're on Windows and bash is not available
            if platform.system() == "Windows":
                # Check if bash is available
                try:
                    subprocess.run(
                        ["bash", "--version"], capture_output=True, check=True
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    typer.echo(
                        "⚠️  Bash not available on Windows. Install Git Bash or WSL to run shell scripts."
                    )
                    typer.echo(
                        "Alternatively, run the commands manually or use PowerShell equivalent."
                    )
                    return

            result = subprocess.run(
                ["bash", str(gen_script)], capture_output=True, text=True
            )
            if result.returncode == 0:
                typer.echo("Documentation regenerated successfully.")
            else:
                typer.echo(f"Error running gen_docs.sh: {result.stderr}")
        else:
            typer.echo("gen_docs.sh script not found.")
    except Exception as e:
        typer.echo(f"Error regenerating docs: {e}")


@app.command("snapshot-healthcheck")
def snapshot_healthcheck():
    """Run snapshot health check."""
    typer.echo("Running snapshot health check...")

    try:
        # Run built-in CLI flows: snapshot report and verify
        import subprocess
        import sys
        from pathlib import Path

        # Run snapshot report
        report_result = subprocess.run(
            [sys.executable, "-m", "xsarena", "ops", "snapshot", "report"],
            capture_output=True,
            text=True,
        )
        if report_result.returncode == 0:
            typer.echo("✓ Snapshot report generated successfully.")
        else:
            typer.echo(f"✗ Error with snapshot report: {report_result.stderr}")

        # Run snapshot verify with ultra-tight mode
        verify_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "xsarena",
                "ops",
                "snapshot",
                "verify",
                "--mode",
                "ultra-tight",
                "--quiet",
            ],
            capture_output=True,
            text=True,
        )
        if verify_result.returncode == 0:
            typer.echo("✓ Snapshot verify completed successfully.")
        else:
            typer.echo(f"✗ Error with snapshot verify: {verify_result.stderr}")

        # Also check for existing snapshot files
        snapshot_files = (
            list(Path(".").glob("xsa_*.txt"))
            + list(Path(".").glob("xsa_*.tar.gz"))
            + list(Path(".").glob("repo_flat*.txt"))
        )
        typer.echo(f"Found {len(snapshot_files)} potential snapshot files.")
        for sf in snapshot_files[:5]:  # Show first 5 files
            size = sf.stat().st_size
            typer.echo(f"  {sf.name}: {size} bytes")
        if len(snapshot_files) > 5:
            typer.echo(f"  ... and {len(snapshot_files) - 5} more files")
    except Exception as e:
        typer.echo(f"Error running snapshot health check: {e}")


@app.command("declutter-phase1")
def declutter_phase1():
    """Run declutter phase 1 (move legacy files, create deprecation stubs)."""
    ROOT = Path(".").resolve()
    LEGACY = ROOT / "legacy"
    CONTRIB_TUI = ROOT / "contrib" / "tui"

    def ensure_dirs():
        LEGACY.mkdir(parents=True, exist_ok=True)
        CONTRIB_TUI.mkdir(parents=True, exist_ok=True)

    def backup_if_exists(p: Path):
        if p.exists():
            ts = time.strftime("%Y%m%d-%H%M%S")
            bak = p.with_suffix(p.suffix + f".bak.{ts}")
            try:
                import shutil

                shutil.copy2(p, bak)
                return str(bak)
            except Exception:
                return None
        return None

    def move_if_exists(src: Path, dst: Path):
        if not src.exists():
            return None
        dst.parent.mkdir(parents=True, exist_ok=True)
        # if same file already there, skip
        if dst.exists():
            return f"already @ {dst}"
        import shutil

        shutil.move(str(src), str(dst))
        return f"moved → {dst}"

    def write_file(path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def stub_xsarena_tui():
        path = ROOT / "xsarena_tui.py"
        content = """#!/usr/bin/env python3
import sys, runpy
print("Deprecated: TUI moved to contrib/tui/xsarena_tui.py; prefer `xsarena serve`.", file=sys.stderr)
sys.exit(runpy.run_path("contrib/tui/xsarena_tui.py") or 0)
"""
        write_file(path, content)
        try:
            import os

            os.chmod(path, 0o755)
        except Exception:
            pass

    def stub_lma_tui():
        path = ROOT / "lma_tui.py"
        content = """#!/usr/bin/env python3
import sys, runpy
print("Deprecated: LMA TUI moved to legacy/lma_tui.py; prefer `xsarena serve`.", file=sys.stderr)
sys.exit(runpy.run_path("legacy/lma_tui.py") or 0)
"""
        write_file(path, content)
        try:
            import os

            os.chmod(path, 0o755)
        except Exception:
            pass

    def write_deprecations():
        p = ROOT / "DEPRECATIONS.md"
        text = """# DEPRECATIONS

These entrypoints are deprecated and retained for one release cycle.

- xsarena_tui.py — moved to contrib/tui/xsarena_tui.py. Prefer `xsarena serve` for web preview.
- lma_tui.py — moved to legacy/lma_tui.py (compat only).
- lma_cli.py — already a deprecation shim; prefer `xsarena`.
- lma_stream.py / lma_templates.py — retained for compatibility with legacy clients; will be pruned in a later phase.

Policy: Keep shims one cycle with a stderr warning, then remove once downstream scripts are updated.
"""
        write_file(p, text)

    def fix_init_docstring():
        initp = ROOT / "src" / "xsarena" / "__init__.py"
        if not initp.exists():
            return "skip (file not found)"
        txt = initp.read_text(encoding="utf-8")
        new = txt.replace("LMASudio", "XSArena")
        if new != txt:
            backup_if_exists(initp)
            write_file(initp, new)
            return "docstring fixed"
        return "ok (unchanged)"

    print("== declutter phase 1 ==")
    ensure_dirs()

    # Moves
    results = {}
    results["xsarena_tui.py"] = move_if_exists(
        ROOT / "xsarena_tui.py", CONTRIB_TUI / "xsarena_tui.py"
    )
    results["lma_tui.py"] = move_if_exists(ROOT / "lma_tui.py", LEGACY / "lma_tui.py")

    # Stubs
    stub_xsarena_tui()
    stub_lma_tui()

    # Docs + init fix
    write_deprecations()
    init_status = fix_init_docstring()

    print("Moves:", results)
    print("init:", init_status)
    print("Done. Phase 1 complete.")


@app.command("lock-directives")
def lock_directives():
    """Generate .xsarena/directives.lock file containing hashes of all directive files."""
    import hashlib
    from datetime import datetime

    # Create the .xsarena directory if it doesn't exist
    xsarena_dir = Path(".xsarena")
    xsarena_dir.mkdir(exist_ok=True)

    # Find all directive files
    directive_files = []

    # Look for directives in various locations
    directives_dir = Path("directives")
    if directives_dir.exists():
        # Find all markdown files in the directives directory
        for file_path in directives_dir.rglob("*.md"):
            directive_files.append(file_path)

    # Calculate hashes for each directive file
    directive_hashes = {}
    for file_path in directive_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            hash_value = hashlib.sha256(content.encode()).hexdigest()
            # Use relative path as the key
            relative_path = str(file_path.relative_to(Path(".")))
            directive_hashes[relative_path] = hash_value
        except Exception as e:
            typer.echo(f"Warning: Could not hash {file_path}: {e}", err=True)

    # Create the lock file
    lock_file = xsarena_dir / "directives.lock"
    lock_data = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "directives": directive_hashes,
    }

    # Write the lock file
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2, ensure_ascii=False)

    typer.echo(f"Directives lockfile created: {lock_file}")
    typer.echo(f"Locked {len(directive_hashes)} directive files")
