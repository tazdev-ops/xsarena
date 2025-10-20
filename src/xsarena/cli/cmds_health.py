"""Health and maintenance commands for XSArena."""

from __future__ import annotations

import contextlib
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import typer
import yaml

from ..utils.secrets_scanner import scan_secrets
from .context import CLIContext

app = typer.Typer(help="System health, maintenance, and self-healing operations.")

# --- Fix Commands ---


@app.command("fix-run")
def fix_run(ctx: typer.Context):
    """Self-heal common configuration/state issues."""
    cli: CLIContext = ctx.obj
    notes = cli.fix()
    typer.echo("=== Fix summary ===")
    for n in notes:
        typer.echo(f"  - {n}")
    typer.echo("Done.")


# --- Clean Commands ---

HEADER_RX = re.compile(r"XSA-EPHEMERAL.*?ttl=(\\d+)([dh])", re.IGNORECASE)


def _load_policy() -> Dict[str, Any]:
    p = Path(".xsarena/cleanup.yml")
    if not p.exists():
        return {"policy": [], "ignore": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {"policy": [], "ignore": []}


def _ttl_from_header(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            head = f.read(1024)
        m = HEADER_RX.search(head)
        if not m:
            return None
        val, unit = int(m.group(1)), m.group(2).lower()
        return val if unit == "d" else max(1, val // 24)
    except Exception:
        return None


def _older_than(path: Path, days: int) -> bool:
    try:
        st = path.stat()
        mtime = datetime.fromtimestamp(st.st_mtime)
    except Exception:
        return False
    return mtime < datetime.now() - timedelta(days=days)


def _glob_all(globs: List[str]) -> List[Path]:
    out: List[Path] = []
    for g in globs:
        out.extend(Path(".").glob(g))
    # unique, files only
    unique = []
    seen = set()
    for p in out:
        if p.is_file() and str(p) not in seen:
            unique.append(p)
            seen.add(str(p))
    return unique


def _match_ignore(path: Path, ignore: List[str]) -> bool:
    from fnmatch import fnmatch

    s = str(path)
    return any(fnmatch(s, ig) for ig in ignore)


@app.command("sweep")
def sweep(
    ttl_override: int = typer.Option(
        None, "--ttl", help="Override TTL (days) for all matches"
    ),
    apply: bool = typer.Option(
        False, "--apply/--dry", help="Apply deletions (default dry-run)"
    ),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Print actions"),
):
    """
    Purge ephemeral artifacts by TTL:
    - Matches .xsarena/cleanup.yml policy globs
    - Honors XSA-EPHEMERAL ttl header which overrides policy TTL
    - Removes empty directories after file deletions
    """
    pol = _load_policy()
    total = 0
    deleted = 0

    # Build candidate set
    candidates: List[Path] = []
    for rule in pol.get("policy", []):
        globs = rule.get("globs") or []
        candidates += _glob_all(globs)
    # Unique candidates
    cand = []
    seen = set()
    ign = pol.get("ignore") or []
    for p in candidates:
        if str(p) in seen:
            continue
        seen.add(str(p))
        if _match_ignore(p, ign):
            continue
        cand.append(p)

    # Evaluate TTL + delete
    for p in cand:
        total += 1
        ttl_days = ttl_override
        if ttl_days is None:
            # header override
            ttl_days = _ttl_from_header(p)
        if ttl_days is None:
            # policy ttl for this file (first matching rule with ttl)
            ttl_days = 7  # fallback
            for rule in pol.get("policy", []):
                if any(p.match(g) for g in (rule.get("globs") or [])):
                    ttl_days = int(rule.get("ttl_days", ttl_days))
                    break
        if ttl_days <= 0:
            continue
        if _older_than(p, ttl_days):
            if verbose:
                typer.echo(f"[delete] {p}  (older than {ttl_days}d)")
            if apply:
                try:
                    p.unlink()
                    deleted += 1
                except Exception as e:
                    typer.echo(f"[warn] failed to delete {p}: {e}", err=True)

    # Remove empty dirs in common hot spots
    for root in [
        Path(".xsarena/jobs"),
        Path("review"),
        Path("snapshot_chunks"),
        Path(".xsarena/tmp"),
    ]:
        if not root.exists():
            continue
        for d in sorted(root.rglob("*"), key=lambda x: len(str(x)), reverse=True):
            if d.is_dir():
                try:
                    next(d.iterdir())
                except StopIteration:
                    if verbose:
                        typer.echo(f"[rmdir] {d}")
                    if apply:
                        with contextlib.suppress(Exception):
                            d.rmdir()

    typer.echo(
        f"Checked {total} file(s). Deleted {deleted}. Mode={'APPLY' if apply else 'DRY'}."
    )


@app.command("scan-secrets")
def clean_scan_secrets(
    path: str = typer.Option(".", "--path", help="Path to scan for secrets"),
    no_fail: bool = typer.Option(
        False, "--no-fail", help="Don't exit with error code on hits"
    ),
):
    """Scan for secrets (API keys, passwords, etc.) in working tree."""
    try:
        findings, has_secrets = scan_secrets(path, fail_on_hits=not no_fail)
        if has_secrets and not no_fail:
            raise typer.Exit(1)
        elif not has_secrets:
            typer.echo("✅ No secrets found.")
    except Exception as e:
        typer.echo(f"Error during scan: {e}")
        raise typer.Exit(1)


@app.command("mark")
def mark_ephemeral(
    path: str, ttl: str = typer.Option("3d", "--ttl", help="TTL e.g., 3d or 72h")
):
    """Add an XSA-EPHEMERAL header to a helper script so the sweeper can purge it later."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        typer.echo("Path not found or not a file.")
        raise typer.Exit(1)
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "XSA-EPHEMERAL" in txt[:512]:
            typer.echo("Already marked.")
            return
        header = f"# XSA-EPHEMERAL ttl={ttl}\\n"
        p.write_text(header + txt, encoding="utf-8")
        typer.echo(f"Marked ephemeral → {p}")
    except Exception as e:
        typer.echo(f"Failed to mark: {e}")
        raise typer.Exit(1)


# --- Boot Commands ---

OPS_DIR = Path(".xsarena/ops")
STARTUP = OPS_DIR / "startup.yml"
POINTERS = OPS_DIR / "pointers.json"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _load_ptr() -> dict:
    if POINTERS.exists():
        try:
            return json.loads(_read(POINTERS))
        except Exception:
            return {}
    return {}


def _save_ptr(d: dict):
    _write(POINTERS, json.dumps(d, indent=2))


def _maybe_merge():
    """
    Pure Python replacement for merge_session_rules.sh
    Reads all *.md under directives/_rules/sources/, concatenates with separators
    """
    sources_dir = Path("directives/_rules/sources")
    merged_file = Path("directives/_rules/rules.merged.md")

    if sources_dir.exists():
        # Collect all .md files in the sources directory
        md_files = list(sources_dir.glob("*.md"))
        if md_files:
            merged_content = []
            for md_file in sorted(md_files):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    merged_content.append(content)
                    merged_content.append("\n---\n\n")  # separator
                except Exception:
                    continue  # skip files that can't be read

            # Write the merged content
            if merged_content:
                # Remove the last separator
                merged_content = merged_content[:-1] if merged_content else []
                merged_text = "".join(merged_content)
                merged_file.parent.mkdir(parents=True, exist_ok=True)
                merged_file.write_text(merged_text, encoding="utf-8")
                return True  # Successfully merged in Python
    return False  # No merge happened


@app.command("merge-rules")
def merge_rules():
    """
    Merge all rules from directives/_rules/sources/ into directives/_rules/rules.merged.md
    """
    success = _maybe_merge()
    if success:
        typer.echo("✓ Merged rules to directives/_rules/rules.merged.md")
    else:
        typer.echo("⚠ No source rules found to merge")


@app.command("read")
def boot_read(verbose: bool = typer.Option(True, "--verbose/--quiet")):
    """Read startup plan; attempt merge; print sources found. Does not modify code."""
    plan = _load_yaml(STARTUP)
    ro = plan.get("read_order", [])
    seen = []
    for item in ro:
        if isinstance(item, dict):
            path = item.get("path")
            if not path:
                continue
            p = Path(path)
            if p.exists():
                seen.append(path)
            else:
                # if_missing flow
                fm = item.get("if_missing", {})
                if fm.get("run") and "merge_session_rules.sh" in fm["run"]:
                    _maybe_merge()
                    if p.exists():
                        seen.append(path)
                        continue
                # fallbacks
                for fb in fm.get("fallback", []) or []:
                    pf = Path(fb)
                    if pf.exists():
                        seen.append(fb)
                        break
        elif isinstance(item, str):
            p = Path(item)
            if p.exists():
                seen.append(item)

    if verbose:
        typer.echo("=== Startup Read Summary ===")
        if seen:
            for s in seen:
                typer.echo(f"  ✓ {s}")
        else:
            typer.echo("  (none found)")

    # Pointers update
    ptr = _load_ptr()
    ptr["last_startup_read"] = _ts()
    if "directives/_rules/sources/ORDERS_LOG.md" in seen:
        ptr["last_order"] = "directives/_rules/sources/ORDERS_LOG.md"
    _save_ptr(ptr)


@app.command("init")
def boot_init():
    """One-time helper: create a minimal rules baseline if merged rules and sources are missing."""
    merged = Path("directives/_rules/rules.merged.md")
    src_rules = Path("directives/_rules/sources/CLI_AGENT_RULES.md")
    if not merged.exists() and not src_rules.exists():
        # Create minimal source then attempt merge
        Path("directives/_rules/sources").mkdir(parents=True, exist_ok=True)
        src_rules.write_text(
            '# CLI Agent Rules (Minimal)\\n- xsarena fix run\\n- xsarena run book "Subject"\\n',
            encoding="utf-8",
        )
        _maybe_merge()
    typer.echo("[boot] init complete.")


@app.command("quick")
def quick_health():
    """Quick health check - verify core functionality."""
    import subprocess
    import sys

    commands_to_test = [
        [sys.executable, "-m", "xsarena", "--help"],
        [sys.executable, "-m", "xsarena", "run", "book", "Test", "--dry-run"],
        [sys.executable, "-m", "xsarena", "ops", "jobs", "ls"],
    ]

    typer.echo("Running quick health check...")
    all_passed = True

    for i, cmd in enumerate(commands_to_test, 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                typer.echo(f"✓ Test {i}: PASSED")
            else:
                typer.echo(f"✗ Test {i}: FAILED - {result.stderr[:100]}...")
                all_passed = False
        except subprocess.TimeoutExpired:
            typer.echo(f"✗ Test {i}: TIMEOUT")
            all_passed = False
        except Exception as e:
            typer.echo(f"✗ Test {i}: ERROR - {str(e)}")
            all_passed = False

    if all_passed:
        typer.echo("\n✓ All health checks PASSED")
    else:
        typer.echo("\n✗ Some health checks FAILED")
        raise typer.Exit(1)
