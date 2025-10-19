import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

# Import the built-in snapshot simple utility
from xsarena.utils import snapshot_simple

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
    "*.egg-info/**",
    ".ipynb_checkpoints/**",
]

PRESET_AUTHOR_CORE_INCLUDE = [
    "README.md",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/cli/cmds_run.py",
    "src/xsarena/cli/cmds_authoring.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "directives/base/zero2hero.md",
    "directives/style.lossless.md",
    "directives/system/plan_from_seeds.md",
]

PRESET_ULTRA_TIGHT_INCLUDE = [
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "directives/base/zero2hero.md",
    "directives/style.lossless.md",
    "directives/system/plan_from_seeds.md",
]

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command("write")
def snapshot_write(
    out: str = typer.Option(
        None, "--out", "-o", help="Output file path. Defaults to xsa_snapshot.txt."
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
    Generate a snapshot using the smart snapshot builder.

    This tool supports multiple modes and is configurable via .snapshotinclude,
    .snapshotignore, or .snapshot.toml/.snapshot.json files.

    Precedence: CLI flags override values from .snapshot.toml configuration file.
    Use --dry-run to see the effective plan before creating the snapshot.
    """
    # Use the built-in simple snapshot utility directly
    if dry_run:
        snapshot_simple.write_text_snapshot(
            out_path=out,
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
                out_path=out,
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
                out_path=out,
                mode=mode,
                with_git=with_git,
                with_jobs=with_jobs,
                with_manifest=with_manifest,
                git_tracked=git_tracked,
                git_include_untracked=git_include_untracked,
                include_system=False,
                dry_run=dry_run,
            )


@app.command("simple")
def snapshot_simple_cmd(
    out: str = typer.Option(
        None, "--out", "-o", help="Output file path. Defaults to xsa_snapshot.txt."
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
    zip_format: bool = typer.Option(
        False, "--zip", help="Write output as a .zip file with manifest."
    ),
):
    """
    Generate a simple snapshot using the built-in snapshot utility.

    This is a minimal dependency version that directly uses the snapshot_simple module.

    Precedence: CLI flags override values from .snapshot.toml configuration file.
    Use --dry-run to see the effective plan before creating the snapshot.
    """
    if dry_run:
        snapshot_simple.write_text_snapshot(
            out_path=out,
            mode=mode,
            with_git=with_git,
            with_jobs=with_jobs,
            with_manifest=with_manifest,
            git_tracked=False,  # Not using git-tracked mode for simple
            git_include_untracked=False,  # Not including untracked for simple
            include_system=False,
            dry_run=True,
        )
    else:
        if zip_format:
            snapshot_simple.write_zip_snapshot(
                out_path=out,
                mode=mode,
                with_git=with_git,
                with_jobs=with_jobs,
                with_manifest=with_manifest,
                git_tracked=False,
                git_include_untracked=False,
                include_system=False,
                dry_run=False,
            )
        else:
            snapshot_simple.write_text_snapshot(
                out_path=out,
                mode=mode,
                with_git=with_git,
                with_jobs=with_jobs,
                with_manifest=with_manifest,
                git_tracked=False,
                git_include_untracked=False,
                include_system=False,
                dry_run=False,
            )


@app.command("pro")
def snapshot_pro(
    out: str = typer.Option(
        None,
        "--out",
        "-o",
        help="Output file path. Defaults to ~/xsa_snapshot_pro.txt.",
    ),
    max_inline: int = typer.Option(
        100000, "--max-inline", help="Maximum size for inlined content in bytes."
    ),
    include_system: bool = typer.Option(
        True,
        "--include-system",
        help="Include system information (Python version, platform, etc.).",
    ),
    include_git: bool = typer.Option(
        True, "--include-git", help="Include git status and branch information."
    ),
    include_jobs: bool = typer.Option(
        True, "--include-jobs", help="Include comprehensive job summaries with events."
    ),
    include_manifest: bool = typer.Option(
        True, "--include-manifest", help="Include code manifest with SHA-256 hashes."
    ),
    include_rules: bool = typer.Option(
        True, "--include-rules", help="Include canonical rules digest."
    ),
    include_reviews: bool = typer.Option(
        True, "--include-reviews", help="Include review artifacts."
    ),
    include_digest: bool = typer.Option(
        True,
        "--include-digest",
        help="Include combined snapshot digest for integrity verification.",
    ),
):
    """
    Generate a pro snapshot with enhanced debugging capabilities.

    This tool provides comprehensive system state information, especially useful
    when escalating to higher AI systems or for detailed analysis of multi-component issues.

    Precedence: CLI flags override values from .snapshot.toml configuration file.
    Use --dry-run to see the effective plan before creating the snapshot.
    """
    script_path = "tools/snapshot_pro.py"
    if Path(script_path).exists():
        # Use the external tool if it exists
        args = [sys.executable, script_path]

        # Add options
        if out:
            args.extend(["--out", out])
        else:
            args.extend(["--out", "~/xsa_snapshot_pro.txt"])
        if max_inline != 100000:
            args.extend(["--max-inline", str(max_inline)])
        if not include_system:
            args.append("--no-system")
        if not include_git:
            args.append("--no-git")
        if not include_jobs:
            args.append("--no-jobs")
        if not include_manifest:
            args.append("--no-manifest")
        if not include_rules:
            args.append("--no-rules")
        if not include_reviews:
            args.append("--no-reviews")
        if not include_digest:
            args.append("--no-digest")

        typer.echo(f"[pro-snapshot] running: {' '.join(args)}")
        try:
            subprocess.run(args, check=True)
        except subprocess.CalledProcessError as e:
            typer.echo(f"[pro-snapshot] failed: {e}", err=True)
            raise typer.Exit(1)
    else:
        # Use the built-in simple snapshot utility if external tool doesn't exist
        # For pro snapshot, we want to include all context by default
        snapshot_simple.write_pro_snapshot(
            out_path=out,
            max_inline=max_inline,
            include_system=include_system,
            include_git=include_git,
            include_jobs=include_jobs,
            include_manifest=include_manifest,
            include_rules=include_rules,
            include_reviews=include_reviews,
            include_digest=include_digest,
            mode="standard",  # Default to standard mode for pro
        )


@app.command("txt")
def snapshot_txt(
    preset: str = typer.Option(
        "author-core",
        "--preset",
        help="Preset include set: author-core|ultra-tight|custom",
    ),
    out: str = typer.Option("repo_flat.txt", "--out", "-o", help="Output .txt path"),
    include: list[str] = typer.Option(
        None,
        "--include",
        "-I",
        help="Glob/file to include (repeatable). Only used when preset=custom",
    ),
    exclude: list[str] = typer.Option(
        None,
        "--exclude",
        "-X",
        help="Glob to exclude (repeatable). If empty, uses a strict default exclude set",
    ),
    max_per_file: int = typer.Option(
        220_000, "--max-per-file", help="Max bytes per file"
    ),
    total_max: int = typer.Option(4_000_000, "--total-max", help="Total max bytes"),
    git_tracked: bool = typer.Option(
        False, "--git-tracked", help="Use git ls-files as baseline"
    ),
    git_include_untracked: bool = typer.Option(
        False, "--git-include-untracked", help="Also include untracked files"
    ),
    redact: bool = typer.Option(
        True, "--redact/--no-redact", help="Apply redaction to embedded text"
    ),
    repo_map: bool = typer.Option(
        False, "--repo-map/--no-repo-map", help="Add a tiny repo map header"
    ),
):
    """
    Flatten curated files into a single .txt with strict includes/excludes for chatbot upload.
    """
    from ..utils.flatpack_txt import flatten_txt

    preset = (preset or "author-core").lower()
    if preset == "author-core":
        inc = PRESET_AUTHOR_CORE_INCLUDE.copy()
    elif preset == "ultra-tight":
        inc = PRESET_ULTRA_TIGHT_INCLUDE.copy()
    else:
        if not include:
            raise typer.Exit(code=2)
        inc = include

    exc = exclude or PRESET_DEFAULT_EXCLUDE

    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    out_path, notes = flatten_txt(
        out_path=outp,
        include=inc,
        exclude=exc,
        max_bytes_per_file=max_per_file,
        total_max_bytes=total_max,
        use_git_tracked=git_tracked,
        include_untracked=git_include_untracked,
        redact=redact,
        add_repo_map=repo_map,
    )
    for n in notes:
        typer.echo(f"[note] {n}")
    typer.echo(f"[snapshot/txt] wrote → {out_path}")
