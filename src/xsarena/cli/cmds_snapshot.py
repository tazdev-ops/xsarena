import subprocess
import sys
from pathlib import Path

import typer

# Import the built-in snapshot simple utility
from xsarena.utils import snapshot_simple

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command("write")
def snapshot_write(
    out: str = typer.Option(
        None, "--out", "-o", help="Output file path. Defaults to xsa_snapshot.txt."
    ),
    mode: str = typer.Option(
        "minimal", "--mode", help="Snapshot breadth: minimal, standard, or max."
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
        False, "--git-include-untracked", help="Include untracked but not ignored files."
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
    mode: str = typer.Option(
        "minimal", "--mode", help="Snapshot breadth: minimal, standard, or max."
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
        None, "--out", "-o", help="Output file path. Defaults to ~/xsa_snapshot_pro.txt."
    ),
    max_inline: int = typer.Option(
        100000, "--max-inline", help="Maximum size for inlined content in bytes."
    ),
    include_system: bool = typer.Option(
        True, "--include-system", help="Include system information (Python version, platform, etc.)."
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
        True, "--include-digest", help="Include combined snapshot digest for integrity verification."
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
