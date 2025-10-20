import contextlib
import fnmatch
import json
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import typer

# Import the built-in snapshot simple utility
from xsarena.utils import snapshot_simple
from xsarena.utils.flatpack_txt import flatten_txt
from xsarena.utils.secrets_scanner import SecretsScanner

# Preset constants for the txt command
PRESET_DEFAULT_EXCLUDE = [
    ".git/**",
    "venv/**",
    ".venv/**",
    "__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".cache/**",
    "*.pyc",
    "logs/**",
    ".xsarena/**",
    "books/**",
    "review/**",
    "legacy/**",
    "tools/**",
    "scripts/**",
    "tests/**",
    "examples/**",
    "packaging/**",
    "pipelines/**",
    "repo_flat.txt",
    "xsa_snapshot*.txt",
    "xsa_snapshot*.zip",
    "xsa_debug_report*.txt",
    "snapshot_chunks/**",
    "*.egg-info/**",
    ".ipynb_checkpoints/**",
    "repo_flat.txt",
    "xsa_snapshot*.txt",
    "xsa_debug_report*.txt",
    "snapshot_chunks/**",
]

PRESET_AUTHOR_CORE_INCLUDE = [
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/cli/cmds_run.py",
    "src/xsarena/cli/cmds_authoring.py",
    "src/xsarena/cli/cmds_snapshot.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/backends/__init__.py",
    "src/xsarena/core/backends/bridge_v2.py",
    "src/xsarena/utils/flatpack_txt.py",
    "src/xsarena/utils/snapshot_simple.py",
    "src/xsarena/utils/secrets_scanner.py",
    "directives/base/zero2hero.md",
    "directives/system/plan_from_seeds.md",
    "directives/_rules/rules.merged.md",
    "docs/USAGE.md",
    "docs/ARCHITECTURE.md",
    "docs/OPERATING_MODEL.md",
    "docs/COMMANDS_CHEATSHEET.md",
]

PRESET_ULTRA_TIGHT_INCLUDE = [
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/cli/cmds_run.py",
    "src/xsarena/cli/cmds_authoring.py",
    "src/xsarena/cli/cmds_snapshot.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/backends/__init__.py",
    "src/xsarena/core/backends/bridge_v2.py",
    "src/xsarena/utils/flatpack_txt.py",
    "src/xsarena/utils/snapshot_simple.py",
    "src/xsarena/utils/secrets_scanner.py",
    "directives/base/zero2hero.md",
    "directives/system/plan_from_seeds.md",
    "directives/_rules/rules.merged.md",
    "docs/USAGE.md",
    "docs/ARCHITECTURE.md",
    "docs/OPERATING_MODEL.md",
    "docs/COMMANDS_CHEATSHEET.md",
]

# A new preset tuned to produce a ~500–550 KB flat pack in typical repos
# (final size depends on repo shape; budgets below enforce the target).
PRESET_TIGHT_500K_INCLUDE = [
    # Core docs/metadata
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    # CLI and context
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    # Core authoring & orchestrator
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    # Jobs (model + executor + scheduler + store)
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor_core.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/jobs/chunk_processor.py",
    "src/xsarena/core/jobs/processing/*.py",
    # Backends (factory + bridge transport + circuit breaker)
    "src/xsarena/core/backends/__init__.py",
    "src/xsarena/core/backends/bridge_v2.py",
    "src/xsarena/core/backends/circuit_breaker.py",
    "src/xsarena/core/backends/transport.py",
    # Bridge API (just the server; omit HTML and handlers if needed)
    "src/xsarena/bridge_v2/api_server.py",
    # Utils (flat pack + snapshot + health/metrics used by verify)
    "src/xsarena/utils/flatpack_txt.py",
    "src/xsarena/utils/snapshot_simple.py",
    "src/xsarena/utils/snapshot/**/*.py",
    "src/xsarena/utils/helpers.py",
    "src/xsarena/utils/secrets_scanner.py",
    "src/xsarena/utils/metrics.py",
    # Directives essential to authoring
    "directives/base/zero2hero.md",
    "directives/system/plan_from_seeds.md",
    "directives/_rules/rules.merged.md",
    # Key docs
    "docs/USAGE.md",
    "docs/OPERATING_MODEL.md",
]

PRESET_NORMAL_INCLUDE = [
    "README.md",
    "README_FOR_AI.md",
    "COMMANDS_REFERENCE.md",
    "MODULES.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "recipe.example.yml",
    "recipe.schema.json",
    "src/xsarena/__init__.py",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/cli/cmds_run.py",
    "src/xsarena/cli/cmds_snapshot.py",
    "src/xsarena/cli/cmds_authoring.py",
    "src/xsarena/cli/cmds_jobs.py",
    "src/xsarena/core/__init__.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/backends/__init__.py",
    "src/xsarena/core/backends/bridge_v2.py",
    "src/xsarena/modes/bilingual.py",
    "src/xsarena/modes/chad.py",
    "src/xsarena/utils/snapshot_simple.py",
    "src/xsarena/utils/flatpack_txt.py",
    "src/xsarena/utils/secrets_scanner.py",
    "src/xsarena/bridge_v2/api_server.py",
    "directives/base/*.md",
    "directives/system/*.md",
    "directives/_rules/rules.merged.md",
    "docs/ARCHITECTURE.md",
    "docs/USAGE.md",
    "docs/OPERATING_MODEL.md",
    "docs/SNAPSHOT_RULEBOOK.md",
    "docs/COMMANDS_CHEATSHEET.md",
    "docs/Bridge.md",
    "docs/PROJECT_MAP.md",
    ".xsarena/config.yml",
]

PRESET_MAXIMAL_INCLUDE = [
    "README.md",
    "README_FOR_AI.md",
    "COMMANDS_REFERENCE.md",
    "MODULES.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "recipe.example.yml",
    "recipe.schema.json",
    "models.json",
    "xsarena_cli.py",
    "xsarena_doctor.py",
    "src/xsarena/__init__.py",
    "src/xsarena/cli/*.py",
    "src/xsarena/core/*.py",
    "src/xsarena/core/backends/*.py",
    "src/xsarena/core/jobs/*.py",
    "src/xsarena/core/v2_orchestrator/*.py",
    "src/xsarena/core/autopilot/*.py",
    "src/xsarena/modes/*.py",
    "src/xsarena/utils/*.py",
    "src/xsarena/bridge_v2/*.py",
    "src/xsarena/coder/*.py",
    "directives/**/*.md",
    "directives/**/*.yml",
    "directives/**/*.json",
    "docs/**/*.md",
    "data/**/*.json",
    "data/**/*.yml",
    "recipes/**/*.yml",
    ".xsarena/config.yml",
    ".xsarena/session_state.json",
    "scripts/**/*.py",
    "scripts/**/*.sh",
    "review/**/*.md",
    "books/**/*.md",
]

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command(
    "create",
    help="Create a flat snapshot, ideal for chatbot uploads. This is the recommended command.",
)
def snapshot_create(
    mode: str = typer.Option(
        "minimal",
        "--mode",
        help="Preset include set: author-core | ultra-tight | tight-500k | normal | maximal | custom.",
    ),
    out: str = typer.Option("~/repo_flat.txt", "--out", "-o", help="Output .txt path"),
    include: List[str] = typer.Option(
        None,
        "--include",
        "-I",
        help="Glob/file to include (repeatable). Used when mode=custom.",
    ),
    exclude: List[str] = typer.Option(
        None,
        "--exclude",
        "-X",
        help="Glob to exclude (repeatable). Appends to default excludes.",
    ),
    max_per_file: int = typer.Option(
        220_000, "--max-per-file", help="Max bytes per file."
    ),
    total_max: int = typer.Option(
        4_000_000, "--total-max", help="Total max bytes for the snapshot."
    ),
    redact: bool = typer.Option(
        True, "--redact/--no-redact", help="Apply redaction to sensitive info."
    ),
    repo_map: bool = typer.Option(
        True, "--repo-map/--no-repo-map", help="Add a repo map header."
    ),
):
    """
    Flatten curated files into a single .txt. This is the primary tool for creating
    context for LLMs. It defaults to the 'author-core' preset.
    """
    mode_lower = (mode or "minimal").lower()

    # Load presets from external config
    from xsarena.core.snapshot_config import load_snapshot_presets

    presets, _ = load_snapshot_presets()

    # Load presets from external config
    from xsarena.core.snapshot_config import load_snapshot_presets

    presets, _ = load_snapshot_presets()

    if mode_lower in presets:
        inc = presets[mode_lower].get("include", [])
    elif mode_lower == "author-core":
        inc = PRESET_AUTHOR_CORE_INCLUDE
    elif mode_lower == "ultra-tight":
        inc = PRESET_ULTRA_TIGHT_INCLUDE
    elif mode_lower == "tight-500k":
        inc = PRESET_TIGHT_500K_INCLUDE
    elif mode_lower == "normal":
        inc = PRESET_NORMAL_INCLUDE
    elif mode_lower == "maximal":
        inc = PRESET_MAXIMAL_INCLUDE
    elif mode_lower == "custom":
        if not include:
            typer.echo(
                "Error: --mode=custom requires at least one --include flag.", err=True
            )
            raise typer.Exit(code=1)
        inc = include
    else:
        typer.echo(
            f"Error: Unknown mode '{mode}'. Choose from: author-core, ultra-tight, normal, maximal, custom, or configured presets.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Heuristic defaults for budgets per mode (only if user did not override)
    if (
        mode_lower == "tight-500k"
        and total_max == 4_000_000
        and max_per_file == 220_000
    ):
        total_max = 550_000
        max_per_file = 45_000
    elif (
        mode_lower == "ultra-tight"
        and total_max == 4_000_000
        and max_per_file == 220_000
    ):
        total_max = 300_000
        max_per_file = 40_000
    elif (
        mode_lower == "author-core"
        and total_max == 4_000_000
        and max_per_file == 220_000
    ):
        total_max = 300_000
        max_per_file = 40_000
    elif mode_lower == "minimal" and total_max == 4_000_000 and max_per_file == 220_000:
        total_max = 180_000
        max_per_file = 30_000
    elif mode_lower == "normal" and total_max == 4_000_000 and max_per_file == 220_000:
        # Keep normal broader, but closer to ~800k
        total_max = 800_000
        max_per_file = 60_000

    # Combine default excludes with any user-provided excludes
    final_excludes = PRESET_DEFAULT_EXCLUDE + (exclude or [])

    outp = Path(out).expanduser()
    outp.parent.mkdir(parents=True, exist_ok=True)

    try:
        out_path, notes = flatten_txt(
            out_path=outp,
            include=inc,
            exclude=final_excludes,
            max_bytes_per_file=max_per_file,
            total_max_bytes=total_max,
            use_git_tracked=False,  # Simplification: git-tracked can be a separate, advanced command if needed.
            include_untracked=False,
            redact=redact,
            add_repo_map=repo_map,
        )
        for n in notes:
            typer.echo(f"[note] {n}")
        typer.echo(f"✓ Snapshot created successfully → {out_path}")
    except Exception as e:
        typer.echo(f"Error creating snapshot: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("report", help="Generate a size report for common modes (preflight).")
def snapshot_report():
    """
    Build a temporary flat pack for each mode and report the on-disk sizes.
    This helps pick a mode that fits target budgets (e.g., ~500–550 KB).
    """
    modes = [
        ("minimal", PRESET_AUTHOR_CORE_INCLUDE[:0]),  # include list resolved below
        ("ultra-tight", PRESET_ULTRA_TIGHT_INCLUDE),
        ("author-core", PRESET_AUTHOR_CORE_INCLUDE),
        ("tight-500k", PRESET_TIGHT_500K_INCLUDE),
        ("normal", PRESET_NORMAL_INCLUDE),
    ]
    # For minimal we reuse a small subset of ultra-tight for consistency
    minimal_inc = [
        "README.md",
        "COMMANDS_REFERENCE.md",
        "pyproject.toml",
        "src/xsarena/cli/main.py",
        "src/xsarena/cli/registry.py",
        "src/xsarena/cli/context.py",
        "src/xsarena/core/prompt.py",
        "src/xsarena/core/prompt_runtime.py",
        "src/xsarena/core/v2_orchestrator/orchestrator.py",
    ]
    results = []
    for name, inc_list in modes:
        inc = minimal_inc if name == "minimal" else inc_list
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
                tmp_path = Path(tf.name)
            # Build with no size caps to get true sizes
            flatten_txt(
                out_path=tmp_path,
                include=inc,
                exclude=PRESET_DEFAULT_EXCLUDE,
                max_bytes_per_file=100_000_000,  # Very large cap to avoid limiting
                total_max_bytes=100_000_000,    # Very large cap to avoid limiting
                use_git_tracked=False,
                include_untracked=False,
                redact=True,
                add_repo_map=False,
            )
            size = tmp_path.stat().st_size
            results.append((name, size))
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
        finally:
            with contextlib.suppress(Exception):
                os.unlink(str(tmp_path))

    # Print a compact table
    typer.echo("\nSnapshot Mode Size Report (No Size Caps)\n")
    typer.echo(f"{'Mode':<14} {'Size (bytes)':>12}")
    typer.echo("-" * 28)
    for name, sz in results:
        if isinstance(sz, int):
            typer.echo(f"{name:<14} {sz:>12,}")
        else:
            typer.echo(f"{name:<14} {sz:>12}")
    typer.echo(
        "\nTip: Use 'xsarena ops snapshot create --mode tight-500k' for a ~500–550 KB pack."
    )


@app.command(
    "write",
    help="Create a normal snapshot (zip format recommended for most use cases).",
)
def snapshot_write(
    out: str = typer.Option(
        "~/xsa_snapshot.txt", "--out", "-o", help="Output file path."
    ),
    mode: Optional[str] = typer.Option(
        None, "--mode", help="Snapshot breadth: minimal, standard, core_logic, or max."
    ),
    with_git: bool = typer.Option(
        False, "--with-git", help="Include git status information."
    ),
    with_jobs: bool = typer.Option(
        False, "--with-jobs", help="Include a summary of recent jobs."
    ),
    with_manifest: bool = typer.Option(
        False, "--with-manifest", help="Include a code manifest of src/."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be included without creating the file.",
    ),
    git_tracked: bool = typer.Option(
        False, "--git-tracked", help="Use exactly git tracked files (overrides mode)."
    ),
    git_include_untracked: bool = typer.Option(
        False,
        "--git-include-untracked",
        help="Include untracked but not ignored files.",
    ),
    zip_format: bool = typer.Option(
        False, "--zip", help="Write output as a .zip file with manifest."
    ),
):
    """
    Create a normal snapshot (text or zip). Prefer --zip for sharing.
    """
    # Change output to .zip if zip_format is True and using default filename or .txt extension
    if zip_format:
        if out == "~/xsa_snapshot.txt" or out.endswith(".txt"):
            out = "~/xsa_snapshot.zip"
    # Use the built-in simple snapshot utility directly
    out_path = Path(out).expanduser()
    if dry_run:
        snapshot_simple.write_text_snapshot(
            out_path=out_path,
            mode=mode,
            with_git=with_git,
            with_jobs=with_jobs,
            with_manifest=with_manifest,
            git_tracked=git_tracked,
            git_include_untracked=git_include_untracked,
            include_system=False,
            dry_run=True,
        )
    else:
        if zip_format:
            snapshot_simple.write_zip_snapshot(
                out_path=out_path,
                mode=mode,
                with_git=with_git,
                with_jobs=with_jobs,
                with_manifest=with_manifest,
                git_tracked=git_tracked,
                git_include_untracked=git_include_untracked,
                include_system=False,
                dry_run=dry_run,
            )
        else:
            snapshot_simple.write_text_snapshot(
                out_path=out_path,
                mode=mode,
                with_git=with_git,
                with_jobs=with_jobs,
                with_manifest=with_manifest,
                git_tracked=git_tracked,
                git_include_untracked=git_include_untracked,
                include_system=False,
                dry_run=dry_run,
            )


@app.command(
    "debug-report", help="Generate a verbose snapshot for debugging. (Maximal snapshot)"
)
def snapshot_debug_report(
    out: str = typer.Option(
        "~/xsa_debug_report.txt",
        "--out",
        "-o",
        help="Output file path.",
    ),
):
    """
    Generates a comprehensive snapshot with system info, git status, job logs,
    and a full file manifest. This is for debugging purposes ONLY and produces
    a very large file.
    """
    typer.echo("Generating verbose debug report. This may take a moment...")
    # We will call the old 'pro' logic, which is now better named.
    # For simplicity, we can reuse the snapshot_simple implementation for this.
    try:
        out_path = Path(out).expanduser()
        snapshot_simple.write_pro_snapshot(
            out_path=out_path,
            mode="standard",  # A reasonable default for a debug report
            include_system=True,
            include_git=True,
            include_jobs=True,
            include_manifest=True,
            include_rules=True,
            include_reviews=True,
            include_digest=True,
        )
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
        # unreadable → treat as suspicious/binary to be safe
        return True
    if not b:
        return False
    if b"\x00" in b:
        return True
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text_ratio = sum(ch not in text_chars for ch in b) / len(b)
    return non_text_ratio > 0.30


def _parse_flatpack_boundaries(text: str) -> List[Tuple[str, int, bool]]:
    """
    Return list of (relpath, approx_bytes, is_binary_marker).
    Supports both formats:
      - === START FILE: path === ... === END FILE: path ===
      - --- START OF FILE path --- ... --- END OF FILE path ---
    Binary marker line: [BINARY FILE] size=... sha256=...
    """
    lines = text.splitlines()
    entries = []
    i = 0
    start_re_a = re.compile(r"^===\s*START\s+FILE:\s*(.+?)\s*===$")
    end_re_a = re.compile(r"^===\s*END\s+FILE:\s*(.+?)\s*===$")
    start_re_b = re.compile(r"^-{3}\s*START\s+OF\s+FILE\s+(.+?)\s*-{3}$")
    end_re_b = re.compile(r"^-{3}\s*END\s+OF\s+FILE\s+(.+?)\s*-{3}$")
    while i < len(lines):
        m_a = start_re_a.match(lines[i]) or start_re_b.match(lines[i])
        if not m_a:
            i += 1
            continue
        rel = m_a.group(1).strip()
        j = i + 1
        is_binary = False
        size_count = 0
        while j < len(lines):
            # detect binary marker
            if lines[j].startswith("[BINARY FILE]"):
                is_binary = True
            if end_re_a.match(lines[j]) or end_re_b.match(lines[j]):
                break
            size_count += len(lines[j]) + 1  # crude approx of bytes
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
        help="Verify a built flat pack (repo_flat.txt / xsa_snapshot.txt). If omitted, preflight verify.",
    ),
    mode: str = typer.Option(
        "minimal", "--mode", help="Mode to preflight (ignored if --file is provided)"
    ),
    include: List[str] = typer.Option(
        None, "--include", "-I", help="Extra include patterns (preflight)"
    ),
    exclude: List[str] = typer.Option(
        None, "--exclude", "-X", help="Extra exclude patterns (preflight)"
    ),
    git_tracked: bool = typer.Option(False, "--git-tracked"),
    git_include_untracked: bool = typer.Option(False, "--git-include-untracked"),
    max_per_file: int = typer.Option(
        200_000, "--max-per-file", help="Per-file budget (bytes)"
    ),
    total_max: int = typer.Option(
        4_000_000, "--total-max", help="Total budget (bytes, preflight only)"
    ),
    disallow: List[str] = typer.Option(
        ["books/**", "review/**", ".xsarena/**", "tools/**"],
        "--disallow",
        help="Disallow these globs; flag if any included",
    ),
    fail_on: List[str] = typer.Option(
        ["secrets", "oversize", "disallowed", "binary", "missing_required"],
        "--fail-on",
        help="Fail on these categories (repeat flag for multiple)",
    ),
    require: List[str] = typer.Option(
        ["README.md", "pyproject.toml"], "--require", help="Paths that must be present"
    ),
    redaction_expected: bool = typer.Option(
        False,
        "--redaction-expected/--no-redaction-expected",
        help="Postflight: warn/fail if no [REDACTED_*] markers appear at all",
    ),
    policy: Optional[str] = typer.Option(
        None,
        "--policy",
        help="Optional policy .yml (keys: disallow_globs, require, max_per_file, total_max, fail_on)",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress narrative output"),
):
    """
    Verify snapshot health: preflight (what would be included) or postflight (verify a built file).
    Exits non-zero if configured fail_on categories are hit.
    """
    # Load policy file if given (CLI flags override policy)
    if policy:
        try:
            import yaml

            data = yaml.safe_load(Path(policy).read_text(encoding="utf-8")) or {}
            disallow = data.get("disallow_globs", disallow) or disallow
            require = data.get("require", require) or require
            max_per_file = int(data.get("max_per_file", max_per_file))
            total_max = int(data.get("total_max", total_max))
            if "fail_on" in data:
                raw = data["fail_on"]
                if isinstance(raw, str):
                    fail_on = [s.strip() for s in raw.split(",") if s.strip()]
                elif isinstance(raw, list):
                    fail_on = list(raw)
        except Exception as e:
            typer.echo(f"[verify] Warning: could not load policy: {e}")
    else:
        # If no policy is given, try to load default policy from .xsarena/ops/snapshot_policy.yml
        try:
            import yaml

            default_policy_path = Path(".xsarena/ops/snapshot_policy.yml")
            if default_policy_path.exists():
                data = (
                    yaml.safe_load(default_policy_path.read_text(encoding="utf-8"))
                    or {}
                )
                disallow = data.get("disallow_globs", disallow) or disallow
                require = data.get("require", require) or require
                max_per_file = int(data.get("max_per_file", max_per_file))
                total_max = int(data.get("total_max", total_max))
                if "fail_on" in data:
                    raw = data["fail_on"]
                    if isinstance(raw, str):
                        fail_on = [s.strip() for s in raw.split(",") if s.strip()]
                    elif isinstance(raw, list):
                        fail_on = list(raw)
        except Exception as e:
            typer.echo(f"[verify] Warning: could not load default policy: {e}")

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
            typer.echo(f"[verify] files: {total_files}, bytes: {total_bytes}")
            if largest and not quiet:
                typer.echo("[verify] top-10 largest:")
                for rel, sz in largest[:10]:
                    typer.echo(f"  - {rel}  ({sz} bytes)")

    def _fail_if_needed(total_files: int, total_bytes: int) -> int:
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
                        for msg in violations[cat][:25]:  # cap output
                            typer.echo(f"    - {msg}")
                raise typer.Exit(1)
            if not quiet:
                typer.echo("[verify] OK")
        exit_code = 1 if to_fail else 0
        raise typer.Exit(exit_code)

    if snapshot_file:
        # Postflight: parse an existing flat pack (repo_flat.txt or xsa_snapshot.txt)
        p = Path(snapshot_file)
        if not p.exists():
            typer.echo(f"[verify] file not found: {snapshot_file}")
            raise typer.Exit(2)
        text = p.read_text(encoding="utf-8", errors="replace")
        entries = _parse_flatpack_boundaries(text)
        if not entries:
            typer.echo("[verify] no file boundaries detected; is this a flat pack?")
            # Not fatal; continue scanning whole file for redaction marker hint
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

        # Redaction heuristic: if expected, warn/fail if the pack contains no redaction markers at all
        if redaction_expected and "[REDACTED_" not in text:
            violations.setdefault("redaction", []).append(
                "no redaction markers found (heuristic)"
            )

        _print_summary(len(entries), total_bytes, largest)

        # Required files check (by string match in rel)
        present = {rel for rel, _, _ in entries}
        for req in require or []:
            if not any(fnmatch.fnmatch(r, req) for r in present):
                violations["missing_required"].append(req)

        return _fail_if_needed(len(entries), total_bytes)

    # Preflight: collect would-be included files using existing utility
    try:
        cfg = snapshot_simple.read_snapshot_config()
        files = snapshot_simple.collect_paths(
            mode=mode,
            include_git_tracked=git_tracked,
            include_untracked=git_include_untracked,
        )
    except Exception as e:
        typer.echo(f"[verify] collection error: {e}")
        raise typer.Exit(2) from e

    # Apply extra include/exclude if provided
    file_set = {p.resolve() for p in files if Path(p).is_file()}
    if include:
        for pat in include:
            for mp in Path(".").glob(pat):
                if mp.is_file():
                    file_set.add(mp.resolve())
    posix_map = {_posix_path(p): p for p in file_set}
    if exclude:
        to_remove = {rel for rel in posix_map if _glob_any(rel, exclude)}
        for rel in to_remove:
            posix_map.pop(rel, None)

    # Evaluate
    total_bytes = 0
    largest = []
    scanner = SecretsScanner()
    for rel, p in posix_map.items():
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
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
                # Keep output compact; show first hit per file
                first = findings[0]
                violations["secrets"].append(f"{rel} [{first.get('type','secret')}]")
        except Exception:
            # If scanning fails, skip rather than aborting the verify
            pass

    largest.sort(key=lambda t: t[1], reverse=True)
    _print_summary(len(posix_map), total_bytes, largest)

    # Total budget (preflight only)
    if total_bytes > total_max:
        violations["oversize"].append(f"[total] {total_bytes} > {total_max}")

    # Required files must be present (by relpath glob)
    rels = list(posix_map.keys())
    for req in require or []:
        if not any(fnmatch.fnmatch(r, req) for r in rels):
            violations["missing_required"].append(req)

    return _fail_if_needed(len(posix_map), total_bytes)
