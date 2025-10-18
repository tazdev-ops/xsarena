"""Project management commands for XSArena."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

app = typer.Typer(help="Project management commands")


@app.command("config-migrate")
def config_migrate():
    """Migrate from config.jsonc/models.json/model_endpoint_map.json to .xsarena/config.yml."""
    migrated = []

    # Load from old config files if they exist
    old_configs = {}

    if Path("config.jsonc").exists():
        with open("config.jsonc", "r") as f:
            # Handle JSONC (JSON with comments) by removing comments
            content = f.read()
            # Remove lines starting with // (comments)
            lines = [
                line
                for line in content.splitlines()
                if not line.strip().startswith("//")
            ]
            content = "\n".join(lines)
            old_configs["bridge"] = json.loads(content)
            migrated.append("config.jsonc")

    if Path("models.json").exists():
        with open("models.json", "r") as f:
            old_configs["models"] = json.load(f)
            migrated.append("models.json")

    if Path("model_endpoint_map.json").exists():
        with open("model_endpoint_map.json", "r") as f:
            old_configs["model_endpoint_map"] = json.load(f)
            migrated.append("model_endpoint_map.json")

    # Write to .xsarena/config.yml under bridge section
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, "r") as f:
            existing_config = yaml.safe_load(f) or {}
    else:
        existing_config = {}

    # Merge old configs into existing config
    for key, value in old_configs.items():
        existing_config[key] = value

    with open(config_path, "w") as f:
        yaml.safe_dump(existing_config, f, default_flow_style=False)

    typer.echo(
        f"Migrated: {', '.join(migrated) if migrated else 'No config files found'}"
    )
    typer.echo(f"Updated: {config_path}")
    typer.echo("Note: Original files kept in place (deprecated).")


@app.command("bridge-ids")
def bridge_ids(
    set_cmd: bool = typer.Option(
        False, "--set", help="Set bridge session and message IDs"
    ),
    get_cmd: bool = typer.Option(
        False, "--get", help="Get bridge session and message IDs"
    ),
    session: Optional[str] = typer.Option(None, "--session", help="Session ID"),
    message: Optional[str] = typer.Option(None, "--message", help="Message ID"),
):
    """Manage bridge session and message IDs."""
    config_path = Path(".xsarena/config.yml")

    if get_cmd:
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            bridge_config = config.get("bridge", {})
            session_id = bridge_config.get("session_id")
            message_id = bridge_config.get("message_id")
            typer.echo(f"Session ID: {session_id}")
            typer.echo(f"Message ID: {message_id}")
        else:
            typer.echo("No .xsarena/config.yml found")
        return

    if set_cmd:
        if not session or not message:
            typer.echo(
                "Error: Both --session and --message are required for set command"
            )
            raise typer.Exit(code=1)

        # Load existing config
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update bridge section
        if "bridge" not in config:
            config["bridge"] = {}
        config["bridge"]["session_id"] = session
        config["bridge"]["message_id"] = message

        # Write back
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        typer.echo(f"Updated bridge IDs in {config_path}")
        typer.echo(f"Session ID: {session}")
        typer.echo(f"Message ID: {message}")


@app.command("bridge-flags")
def bridge_flags(
    tavern: Optional[str] = typer.Option(
        None, "--tavern", help="Enable/disable tavern mode (on/off)"
    ),
    bypass: Optional[str] = typer.Option(
        None, "--bypass", help="Enable/disable bypass mode (on/off)"
    ),
    idle: Optional[str] = typer.Option(
        None, "--idle", help="Enable/disable idle restart (on/off)"
    ),
    timeout: Optional[int] = typer.Option(
        None, "--timeout", help="Stream response timeout in seconds"
    ),
):
    """Manage bridge configuration flags."""
    config_path = Path(".xsarena/config.yml")

    # Load existing config
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Ensure bridge section exists
    if "bridge" not in config:
        config["bridge"] = {}

    # Update flags if provided
    updates = []

    if tavern is not None:
        if tavern.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["tavern_mode_enabled"] = True
            updates.append("tavern_mode_enabled = true")
        elif tavern.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["tavern_mode_enabled"] = False
            updates.append("tavern_mode_enabled = false")
        else:
            typer.echo("Error: --tavern must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if bypass is not None:
        if bypass.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["bypass_enabled"] = True
            updates.append("bypass_enabled = true")
        elif bypass.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["bypass_enabled"] = False
            updates.append("bypass_enabled = false")
        else:
            typer.echo("Error: --bypass must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if idle is not None:
        if idle.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["enable_idle_restart"] = True
            updates.append("enable_idle_restart = true")
        elif idle.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["enable_idle_restart"] = False
            updates.append("enable_idle_restart = false")
        else:
            typer.echo("Error: --idle must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if timeout is not None:
        if timeout < 0:
            typer.echo("Error: --timeout must be a non-negative integer")
            raise typer.Exit(code=1)
        config["bridge"]["stream_response_timeout_seconds"] = timeout
        updates.append(f"stream_response_timeout_seconds = {timeout}")

    # Write back to config file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    typer.echo(f"Updated bridge flags in {config_path}")
    for update in updates:
        typer.echo(f"  {update}")


@app.command("normalize")
def normalize():
    """Apply content fixes and cleanup (normalize, declutter)."""
    typer.echo("Applying normalization and cleanup...")

    # Apply content fixes (similar to apply_content_fixes.sh)
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        dirs[:] = [
            d
            for d in dirs
            if d not in [".git", ".venv", "venv", "__pycache__", ".xsarena"]
        ]

        for file in files:
            if file.endswith((".py", ".md", ".txt", ".json", ".yml", ".yaml")):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding="utf-8")
                    # Apply basic fixes like removing trailing whitespace
                    lines = content.splitlines()
                    fixed_lines = [line.rstrip() for line in lines]
                    fixed_content = "\n".join(fixed_lines)

                    if content != fixed_content:
                        filepath.write_text(fixed_content, encoding="utf-8")
                        typer.echo(f"Fixed: {filepath}")
                except Exception:
                    pass  # Skip files that can't be read

    # Apply declutter (similar to declutter_phase2.sh)
    # Remove common temp files
    temp_patterns = ["*.tmp", "*.temp", "*.bak", "*~", ".DS_Store"]
    for pattern in temp_patterns:
        for temp_file in Path(".").glob(f"**/{pattern}"):
            try:
                temp_file.unlink()
                typer.echo(f"Removed: {temp_file}")
            except Exception:
                pass

    typer.echo("Normalization and cleanup complete.")


@app.command("directives-merge")
def directives_merge():
    """Merge session rules from directives/_rules into directives/_rules/rules.merged.md."""
    typer.echo("Merging session rules...")

    rules_dir = Path("directives/_rules")
    sources_dir = rules_dir / "sources"
    output_file = rules_dir / "rules.merged.md"

    if not sources_dir.exists():
        typer.echo("Sources directory not found.")
        return

    merged_content = []
    for source_file in sources_dir.glob("*.md"):
        try:
            content = source_file.read_text(encoding="utf-8")
            merged_content.append(f"<!-- Source: {source_file.name} -->\n")
            merged_content.append(content)
            merged_content.append("\n---\n\n")  # Separator
        except Exception as e:
            typer.echo(f"Error reading {source_file}: {e}")

    if merged_content:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("".join(merged_content), encoding="utf-8")
        typer.echo(f"Merged rules to: {output_file}")

    # Run deduplication if the script exists
    dedupe_script = Path("tools/dedupe_rules_merged.py")
    if dedupe_script.exists():
        import subprocess

        try:
            result = subprocess.run(
                [sys.executable, str(dedupe_script)], capture_output=True, text=True
            )
            if result.returncode == 0:
                typer.echo("Rules deduplication completed.")
            else:
                typer.echo(f"Deduplication failed: {result.stderr}")
        except Exception as e:
            typer.echo(f"Error running deduplication: {e}")


@app.command("docs-regen")
def docs_regen():
    """Regenerate documentation (help files, etc.)."""
    typer.echo("Regenerating documentation...")

    # This would typically call the gen_docs.sh script logic
    # For now, we'll simulate the process
    import platform
    import subprocess

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
        # Perform a dry run to verify snapshot functionality
        import subprocess
        import sys
        from pathlib import Path

        script_path = "tools/snapshot_builder.py"
        if Path(script_path).exists():
            args = [sys.executable, script_path, "--dry-run"]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0:
                typer.echo("Snapshot health check completed successfully.")
                typer.echo("Snapshot builder is working correctly.")
            else:
                typer.echo(f"Error with snapshot builder: {result.stderr}")
        else:
            typer.echo("Snapshot builder not found at 'tools/snapshot_builder.py'")

        # Also check for existing snapshot files
        snapshot_files = list(Path(".").glob("xsa_*.txt")) + list(
            Path(".").glob("xsa_*.tar.gz")
        )
        typer.echo(f"Found {len(snapshot_files)} potential snapshot files.")
        for sf in snapshot_files:
            size = sf.stat().st_size
            typer.echo(f"  {sf.name}: {size} bytes")
    except Exception as e:
        typer.echo(f"Error running snapshot health check: {e}")


@app.command("declutter-phase1")
def declutter_phase1():
    """Run declutter phase 1 (move legacy files, create deprecation stubs)."""
    import time
    from pathlib import Path

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


@app.command("dedupe-by-hash")
def dedupe_by_hash(
    apply_changes: bool = typer.Option(
        False, "--apply", help="Apply changes (default is dry-run)"
    )
):
    """Remove duplicate files by hash (dry-run by default)."""
    import subprocess
    from pathlib import Path

    # Check if required files exist
    dup_hashes_path = Path("review/dup_hashes.txt")
    books_sha256_path = Path("review/books_sha256.txt")

    if not dup_hashes_path.exists():
        typer.echo(f"Error: {dup_hashes_path} not found")
        raise typer.Exit(code=1)

    if not books_sha256_path.exists():
        typer.echo(f"Error: {books_sha256_path} not found")
        raise typer.Exit(code=1)

    # Read duplicate hashes
    with open(dup_hashes_path, "r", encoding="utf-8") as f:
        dup_hashes = [line.strip() for line in f if line.strip()]

    for hash_val in dup_hashes:
        # Get files for this hash
        # Pure Python grep replacement for portability
        lines_for_hash = []
        with open(books_sha256_path, "r", encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip().startswith(f"{hash_val} "):
                    lines_for_hash.append(ln.rstrip("\n"))
        if not lines_for_hash:
            continue
        files = []
        for ln in lines_for_hash:
            parts = ln.split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])

        if len(files) < 2:
            continue  # Need at least 2 files to have duplicates

        # Find the file with the newest modification time
        keep = ""
        newest_mtime = 0
        for f in files:
            try:
                mt = Path(f).stat().st_mtime
            except Exception:
                mt = 0

            if mt > newest_mtime:
                newest_mtime = mt
                keep = f

        # Archive duplicates
        for f in files:
            if f == keep:
                continue
            typer.echo(f"archive dup: {f} (keep: {keep})")
            if apply_changes:
                import os

                os.makedirs("books/archive", exist_ok=True)
                try:
                    # Try git mv first, then regular mv
                    subprocess.run(
                        ["git", "mv", f, f"books/archive/{os.path.basename(f)}"],
                        capture_output=True,
                    )
                except Exception:
                    import shutil

                    shutil.move(f, f"books/archive/{os.path.basename(f)}")

    if not apply_changes:
        typer.echo("Dry-run. Re-run with --apply to apply changes.")


@app.command("lock-directives")
def lock_directives():
    """Generate .xsarena/directives.lock file containing hashes of all directive files."""
    import hashlib
    import json
    from datetime import datetime
    from pathlib import Path

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


@app.command("init")
def project_init_cmd(
    dir_path: str = typer.Option(
        ".", "--dir", help="Directory to initialize (default: current directory)"
    )
):
    """Initialize XSArena project structure (.xsarena/, books/, etc.) and index directives if present."""
    import os

    root_dir = os.path.abspath(dir_path)
    xsarena_dir = os.path.join(root_dir, ".xsarena")

    created_paths = []

    # Create .xsarena directory and subdirectories
    os.makedirs(xsarena_dir, exist_ok=True)
    created_paths.append(xsarena_dir)

    finals_dir = os.path.join(xsarena_dir, "finals")
    os.makedirs(finals_dir, exist_ok=True)
    created_paths.append(finals_dir)

    outlines_dir = os.path.join(xsarena_dir, "outlines")
    os.makedirs(outlines_dir, exist_ok=True)
    created_paths.append(outlines_dir)

    review_dir = os.path.join(root_dir, "review")
    os.makedirs(review_dir, exist_ok=True)
    created_paths.append(review_dir)

    # Create minimal .xsarena/config.yml if it doesn't exist
    config_path = os.path.join(xsarena_dir, "config.yml")
    if not os.path.exists(config_path):
        minimal_config = """# XSArena Configuration
# This file contains user/project defaults for XSArena

# Bridge configuration (for connecting to LMArena through browser)
# bridge:
#   session_id: "your-session-id"
#   message_id: "your-message-id"
#   tavern_mode_enabled: false
#   bypass_enabled: false
#   enable_idle_restart: true
#   stream_response_timeout_seconds: 300

# Default model and backend settings
# model: "default"
# backend: "bridge"
# window_size: 100

# Output and continuation settings
# output_min_chars: 50
# output_push_max_passes: 3
# continuation_mode: "auto"
# anchor_length: 200
# repetition_threshold: 0.8
# repetition_warn: true
# smart_min_enabled: true
# outline_first_enabled: false
# semantic_anchor_enabled: true
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(minimal_config)
        created_paths.append(config_path)

    # Run directives index if directives/ exists
    directives_dir = os.path.join(root_dir, "directives")
    if os.path.exists(directives_dir):
        typer.echo("Indexing directives...")
        try:
            from .cmds_directives import directives_index as directives_index_func

            # Call the index command function directly
            directives_index_func(out="directives/manifest.yml")  # Use default output
            created_paths.append("directives indexed")
        except Exception as e:
            typer.echo(f"Warning: Could not index directives: {e}")

    typer.echo("XSArena project initialized successfully!")
    typer.echo("Created paths:")
    for path in created_paths:
        typer.echo(f"  - {path}")

    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  1. Start the bridge: xsarena service start-bridge-v2")
    typer.echo("  2. Install the userscript: xsarena_bridge.user.js")
    typer.echo("  3. Begin capturing session IDs: /capture in interactive mode")
    typer.echo("  4. Start authoring: xsarena interactive or xsarena run")


if __name__ == "__main__":
    app()
