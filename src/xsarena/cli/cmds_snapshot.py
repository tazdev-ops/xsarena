import contextlib
import fnmatch
import json
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from xsarena.utils.flatpack_txt import flatten_txt
from xsarena.utils.secrets_scanner import SecretsScanner
from xsarena.utils.snapshot_simple import write_pro_snapshot

# --- New, Refined Presets ---

# Ultra-tight preset for quick sharing with AI assistants.
PRESET_ULTRA_TIGHT_INCLUDE = [
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    "docs/ARCHITECTURE.md",
    "docs/USAGE.md",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/config.py",
    "directives/_rules/rules.merged.md",
]

# Refined author-core preset. Includes more source code and the directives manifest.
PRESET_AUTHOR_CORE_INCLUDE = [
    # Core docs and metadata
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    # Essential architecture & usage docs
    "docs/ARCHITECTURE.md",
    "docs/USAGE.md",
    "docs/OPERATING_MODEL.md",
    # All source code
    "src/xsarena/**/*.py",
    # Directives MANIFEST, not all the tiny files
    "directives/manifest.yml",
    "directives/_rules/rules.merged.md",
    # Key data schemas/resources
    "data/schemas/**/*.json",
    "data/resource_map.en.json",
    # Project configuration
    ".xsarena/config.yml",
]

# Sensible global excludes (can be extended via env)
PRESET_DEFAULT_EXCLUDE = [
    ".git/**",
    "venv/**",
    ".venv/**",
    "__pycache__/**",
    "*.pyc",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".cache/**",
    "dist/**",
    "build/**",
    "logs/**",
    ".xsarena/jobs/**",
    ".xsarena/tmp/**",
    "books/**",
    "review/**",
    "tests/**",
    "examples/**",
    "*.egg-info/**",
    ".ipynb_checkpoints/**",
    "repo_flat.txt",
    "xsa_snapshot*.txt",
    "xsa_snapshot*.zip",
    "xsa_debug_report*.txt",
    "snapshot_chunks/**",
    "**/_preview/**",
    "**/_mixer/**",  # Exclude temporary directive directories
]

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command(
    "create",
    help="Create a flat snapshot, ideal for chatbot uploads. Use --mode ultra-tight for the leanest version.",
)
def snapshot_create(
    mode: str = typer.Option(
        "author-core", "--mode", help="ultra-tight | author-core | custom"
    ),
    out: str = typer.Option("~/repo_flat.txt", "--out", "-o", help="Output .txt path"),
    include: List[str] = typer.Option(
        None,
        "--include",
        "-I",
        help="Extra include glob(s) (used in custom mode or appended to preset)",
    ),
    exclude: List[str] = typer.Option(
        None, "--exclude", "-X", help="Extra exclude glob(s)"
    ),
    git_tracked: bool = typer.Option(
        False, "--git-tracked", help="Enumerate files from git ls-files"
    ),
    max_per_file: int = typer.Option(
        180_000, "--max-per-file", help="Max bytes per file"
    ),
    total_max: int = typer.Option(2_500_000, "--total-max", help="Total max bytes"),
    redact: bool = typer.Option(True, "--redact/--no-redact", help="Apply redaction"),
    repo_map: bool = typer.Option(
        True, "--repo-map/--no-repo-map", help="Add repo map header"
    ),
):
    """
    Flatten curated files into a single .txt. Uses glob-based presets and budgets.
    Tip: 'ultra-tight' is best for AI. 'author-core' is more comprehensive.
    """
    mode_lower = (mode or "author-core").lower()

    # Resolve includes based on mode
    if mode_lower == "ultra-tight":
        inc = list(PRESET_ULTRA_TIGHT_INCLUDE)
    elif mode_lower == "author-core":
        inc = list(PRESET_AUTHOR_CORE_INCLUDE)
    elif mode_lower == "custom":
        if not include:
            typer.echo(
                "Error: --mode=custom requires at least one --include (-I)", err=True
            )
            raise typer.Exit(code=1)
        inc = list(include)
    else:
        typer.echo(
            f"Error: Unknown mode '{mode}'. Choose: ultra-tight | author-core | custom",
            err=True,
        )
        raise typer.Exit(code=1)

    if mode_lower != "custom" and include:
        inc.extend(include)  # Append extra includes to presets

    # Resolve excludes (preset + CLI + env override)
    final_excludes = list(PRESET_DEFAULT_EXCLUDE) + (exclude or [])
    env_extra = os.getenv("XSA_SNAPSHOT_EXCLUDE", "").strip()
    if env_extra:
        final_excludes += [pat.strip() for pat in env_extra.split(",") if pat.strip()]

    outp = Path(out).expanduser()

    try:
        out_path, notes = flatten_txt(
            out_path=outp,
            include=inc,
            exclude=final_excludes,
            max_bytes_per_file=max_per_file,
            total_max_bytes=total_max,
            use_git_tracked=git_tracked,
            include_untracked=False,
            redact=redact,
            add_repo_map=repo_map,
        )
        for n in notes:
            typer.echo(f"[note] {n}")

        # Small postflight summary (files embedded and size)
        try:
            text = outp.read_text(encoding="utf-8", errors="replace")
            entries = _parse_flatpack_boundaries(text)
            typer.echo(
                f"✓ Snapshot → {out_path} | files embedded: {len(entries)} | bytes: {outp.stat().st_size:,}"
            )
        except Exception:
            typer.echo(f"✓ Snapshot → {out_path}")

    except Exception as e:
        typer.echo(f"Error creating snapshot: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("report", help="Report true on-disk size for presets (unlimited budgets).")
def snapshot_report():
    """
    Builds temporary flat packs (unlimited budgets) to show raw size of each preset.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
        tmp_path = Path(tf.name)

    try:
        typer.echo("\nSnapshot Mode Size Report\n")
        typer.echo(f"{'Mode':<14} {'Size (bytes)':>12}")
        typer.echo("-" * 28)

        # Test ultra-tight preset
        flatten_txt(
            out_path=tmp_path,
            include=PRESET_ULTRA_TIGHT_INCLUDE,
            exclude=PRESET_DEFAULT_EXCLUDE,
            max_bytes_per_file=999_999_999,
            total_max_bytes=999_999_999,
            use_git_tracked=False,
            include_untracked=False,
            redact=True,
            add_repo_map=False,
        )
        ultra_tight_size = tmp_path.stat().st_size
        typer.echo(f"{'ultra-tight':<14} {ultra_tight_size:>12,}")

        # Test author-core preset
        flatten_txt(
            out_path=tmp_path,
            include=PRESET_AUTHOR_CORE_INCLUDE,
            exclude=PRESET_DEFAULT_EXCLUDE,
            max_bytes_per_file=999_999_999,
            total_max_bytes=999_999_999,
            use_git_tracked=False,
            include_untracked=False,
            redact=True,
            add_repo_map=False,
        )
        author_core_size = tmp_path.stat().st_size
        typer.echo(f"{'author-core':<14} {author_core_size:>12,}")

        typer.echo("\nTip: Use 'xsarena ops snapshot create' to build a snapshot pack.")
    except Exception as e:
        typer.echo(f"Report failed: {e}", err=True)
    finally:
        with contextlib.suppress(Exception):
            os.unlink(str(tmp_path))


@app.command("debug-report", help="Generate a verbose snapshot for debugging.")
def snapshot_debug_report(
    out: str = typer.Option(
        "~/xsa_debug_report.txt", "--out", "-o", help="Output file"
    ),
):
    typer.echo("Generating verbose debug report. This may take a moment...")
    try:
        out_path = Path(out).expanduser()
        write_pro_snapshot(out_path=out_path, mode="standard")
        typer.echo(f"✓ Debug report written to: {out}")
    except Exception as e:
        typer.echo(f"Error creating debug report: {e}", err=True)
        raise typer.Exit(1) from e


def _posix_path(p: Path) -> str:
    try:
        return p.resolve().relative_to(Path(".").resolve()).as_posix()
    except Exception:
        return p.as_posix().replace("\\", "/")


def _glob_any(rel: str, patterns: List[str]) -> bool:
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, pat) for pat in (patterns or []))


def _is_binary_quick(path: Path, sample_bytes: int = 8192) -> bool:
    try:
        b = path.read_bytes()[:sample_bytes]
    except Exception:
        return True
    if not b:
        return False
    if b"\x00" in b:
        return True
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text_ratio = sum(ch not in text_chars for ch in b) / len(b)
    return non_text_ratio > 0.30


def _parse_flatpack_boundaries(text: str) -> List[Tuple[str, int, bool]]:
    lines = text.splitlines()
    entries = []
    i = 0
    start_re = re.compile(r"^===\s*START\s+FILE:\s*(.+?)\s*===$")
    end_re = re.compile(r"^===\s*END\s+FILE:\s*(.+?)\s*===$")
    while i < len(lines):
        m_a = start_re.match(lines[i])
        if not m_a:
            i += 1
            continue
        rel = m_a.group(1).strip()
        j = i + 1
        is_binary = False
        size_count = 0
        while j < len(lines):
            if lines[j].startswith("[BINARY FILE]"):
                is_binary = True
            if end_re.match(lines[j]):
                break
            size_count += len(lines[j]) + 1
            j += 1
        entries.append((rel, size_count, is_binary))
        i = j + 1
    return entries


@app.command("verify")
def snapshot_verify(
    snapshot_file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Verify a built flat pack. If omitted, preflight verify.",
    ),
    mode: str = typer.Option(
        "author-core",
        "--mode",
        help="Mode to preflight (ignored if --file is provided)",
    ),
    include: List[str] = typer.Option(
        None, "--include", "-I", help="Extra include patterns (preflight)"
    ),
    exclude: List[str] = typer.Option(
        None, "--exclude", "-X", help="Extra exclude patterns (preflight)"
    ),
    git_tracked: bool = typer.Option(False, "--git-tracked"),
    max_per_file: int = typer.Option(
        200_000, "--max-per-file", help="Per-file budget (bytes)"
    ),
    total_max: int = typer.Option(
        4_000_000, "--total-max", help="Total budget (bytes, preflight only)"
    ),
    disallow: List[str] = typer.Option(
        PRESET_DEFAULT_EXCLUDE, "--disallow", help="Disallow these globs."
    ),
    fail_on: List[str] = typer.Option(
        ["secrets", "oversize", "disallowed", "binary", "missing_required"],
        "--fail-on",
        help="Fail on these categories.",
    ),
    require: List[str] = typer.Option(
        ["README.md", "pyproject.toml"], "--require", help="Paths that must be present"
    ),
    redaction_expected: bool = typer.Option(
        False,
        "--redaction-expected/--no-redaction-expected",
        help="Postflight: warn/fail if no [REDACTED_*] markers appear.",
    ),
    policy: Optional[str] = typer.Option(
        None, "--policy", help="Optional policy .yml."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress narrative output"),
):
    """
    Verify snapshot health: preflight (what would be included) or postflight (verify a built file).
    Exits non-zero if configured fail_on categories are hit.
    """
    if policy:
        try:
            import yaml

            data = yaml.safe_load(Path(policy).read_text(encoding="utf-8")) or {}
            disallow = data.get("disallow_globs", disallow) or disallow
            require = data.get("require", require) or require
            max_per_file = int(data.get("max_per_file", max_per_file))
            total_max = int(data.get("total_max", total_max))
            fail_on = data.get("fail_on", fail_on)
        except Exception as e:
            typer.echo(f"[verify] Warning: could not load policy: {e}")

    violations = {
        "secrets": [],
        "oversize": [],
        "disallowed": [],
        "binary": [],
        "missing_required": [],
    }

    def _print_summary(
        total_files: int, total_bytes: int, largest: List[Tuple[str, int]]
    ):
        if not json_output:
            typer.echo(f"[verify] files: {total_files}, bytes: {total_bytes:,}")
            if largest and not quiet:
                typer.echo("[verify] top-10 largest:")
                for rel, sz in largest[:10]:
                    typer.echo(f"  - {rel:<60} ({sz:>7,} bytes)")

    def _fail_if_needed(total_files: int, total_bytes: int):
        to_fail = {k for k in violations if violations[k] and k in set(fail_on)}
        if json_output:
            result = {
                "total_files": total_files,
                "total_bytes": total_bytes,
                "violations": violations,
                "categories_to_fail": sorted(to_fail),
                "status": "FAIL" if to_fail else "OK",
            }
            typer.echo(json.dumps(result))
        else:
            if to_fail:
                typer.echo("[verify] FAIL on categories: " + ", ".join(sorted(to_fail)))
                for cat in sorted(to_fail):
                    if not quiet:
                        typer.echo(f"  [{cat}]")
                        for msg in violations[cat][:25]:
                            typer.echo(f"    - {msg}")
                raise typer.Exit(1)
            if not quiet:
                typer.echo("[verify] OK")
        raise typer.Exit(1 if to_fail else 0)

    if snapshot_file:
        p = Path(snapshot_file)
        if not p.exists():
            typer.echo(f"[verify] file not found: {snapshot_file}")
            raise typer.Exit(2)
        text = p.read_text(encoding="utf-8", errors="replace")
        entries = _parse_flatpack_boundaries(text)
        total_bytes = 0
        largest = []
        for rel, approx_bytes, is_bin in entries:
            total_bytes += approx_bytes
            largest.append((rel, approx_bytes))
            if approx_bytes > max_per_file:
                violations["oversize"].append(
                    f"{rel} ({approx_bytes} > {max_per_file})"
                )
            if _glob_any(rel, disallow):
                violations["disallowed"].append(rel)
            if is_bin:
                violations["binary"].append(rel)
        largest.sort(key=lambda t: t[1], reverse=True)
        if redaction_expected and "[REDACTED_" not in text:
            violations.setdefault("redaction", []).append("no redaction markers found")
        _print_summary(len(entries), total_bytes, largest)
        present = {rel for rel, _, _ in entries}
        for req in require or []:
            if not any(fnmatch.fnmatch(r, req) for r in present):
                violations["missing_required"].append(req)
        _fail_if_needed(len(entries), total_bytes)

    # Preflight logic
    if mode == "ultra-tight":
        base_includes = PRESET_ULTRA_TIGHT_INCLUDE
    elif mode == "author-core":
        base_includes = PRESET_AUTHOR_CORE_INCLUDE
    else:
        base_includes = []

    final_includes = base_includes + (include or [])
    final_excludes = PRESET_DEFAULT_EXCLUDE + (exclude or [])

    # Collect files using a simplified glob-based approach
    all_files = {p.resolve() for p in Path(".").rglob("*") if p.is_file()}
    included_files = set()
    for pat in final_includes:
        for p in Path(".").glob(pat):
            if p.is_file():
                included_files.add(p.resolve())

    excluded_files = set()
    for p in included_files:
        if _glob_any(_posix_path(p), final_excludes):
            excluded_files.add(p)

    final_set = included_files - excluded_files
    posix_map = {_posix_path(p): p for p in final_set}

    total_bytes = 0
    largest = []
    scanner = SecretsScanner()
    for rel, p in posix_map.items():
        sz = p.stat().st_size
        total_bytes += sz
        largest.append((rel, sz))
        if sz > max_per_file:
            violations["oversize"].append(f"{rel} ({sz} > {max_per_file})")
        if _glob_any(rel, disallow):
            violations["disallowed"].append(rel)
        if _is_binary_quick(p):
            violations["binary"].append(rel)
        try:
            findings = scanner.scan_file(p)
            if findings:
                violations["secrets"].append(
                    f"{rel} [{findings[0].get('type','secret')}]"
                )
        except Exception:
            pass

    largest.sort(key=lambda t: t[1], reverse=True)
    _print_summary(len(posix_map), total_bytes, largest)
    if total_bytes > total_max:
        violations["oversize"].append(f"[total] {total_bytes:,} > {total_max:,}")

    rels = list(posix_map.keys())
    for req in require or []:
        if not any(fnmatch.fnmatch(r, req) for r in rels):
            violations["missing_required"].append(req)

    _fail_if_needed(len(posix_map), total_bytes)
