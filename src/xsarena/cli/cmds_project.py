"""Project management commands for XSArena."""

import typer
import sys
from pathlib import Path
import json
import yaml
from typing import Optional
import os
import shutil

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
            lines = [line for line in content.splitlines() if not line.strip().startswith("//")]
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
    
    typer.echo(f"Migrated: {', '.join(migrated) if migrated else 'No config files found'}")
    typer.echo(f"Updated: {config_path}")
    typer.echo("Note: Original files kept in place (deprecated).")


@app.command("bridge-ids")
def bridge_ids(
    set_cmd: bool = typer.Option(False, "--set", help="Set bridge session and message IDs"),
    get_cmd: bool = typer.Option(False, "--get", help="Get bridge session and message IDs"),
    session: Optional[str] = typer.Option(None, "--session", help="Session ID"),
    message: Optional[str] = typer.Option(None, "--message", help="Message ID")
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
            typer.echo("Error: Both --session and --message are required for set command")
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


@app.command("normalize")
def normalize():
    """Apply content fixes and cleanup (normalize, declutter)."""
    typer.echo("Applying normalization and cleanup...")
    
    # Apply content fixes (similar to apply_content_fixes.sh)
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in [".git", ".venv", "venv", "__pycache__", ".xsarena"]]
        
        for file in files:
            if file.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml')):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding='utf-8')
                    # Apply basic fixes like removing trailing whitespace
                    lines = content.splitlines()
                    fixed_lines = [line.rstrip() for line in lines]
                    fixed_content = '\n'.join(fixed_lines)
                    
                    if content != fixed_content:
                        filepath.write_text(fixed_content, encoding='utf-8')
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
            content = source_file.read_text(encoding='utf-8')
            merged_content.append(f"<!-- Source: {source_file.name} -->\n")
            merged_content.append(content)
            merged_content.append("\n---\n\n")  # Separator
        except Exception as e:
            typer.echo(f"Error reading {source_file}: {e}")
    
    if merged_content:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("".join(merged_content), encoding='utf-8')
        typer.echo(f"Merged rules to: {output_file}")
    
    # Run deduplication if the script exists
    dedupe_script = Path("tools/dedupe_rules_merged.py")
    if dedupe_script.exists():
        import subprocess
        try:
            result = subprocess.run([sys.executable, str(dedupe_script)], capture_output=True, text=True)
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
    import subprocess
    import sys
    
    try:
        # Try to run the shell script if it exists
        gen_script = Path("scripts/gen_docs.sh")
        if gen_script.exists():
            result = subprocess.run([str(gen_script)], shell=True, capture_output=True, text=True)
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
    
    # This would typically call the snapshot_healthcheck.sh script logic
    import subprocess
    import sys
    
    try:
        # Try to run the shell script if it exists
        hc_script = Path("scripts/snapshot_healthcheck.sh")
        if hc_script.exists():
            result = subprocess.run([str(hc_script)], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                typer.echo("Snapshot health check completed successfully.")
                typer.echo(result.stdout)
            else:
                typer.echo(f"Error running snapshot_healthcheck.sh: {result.stderr}")
        else:
            # Fallback: basic snapshot checks
            snapshot_files = list(Path(".").glob("xsa_*.txt")) + list(Path(".").glob("xsa_*.tar.gz"))
            typer.echo(f"Found {len(snapshot_files)} potential snapshot files.")
            for sf in snapshot_files:
                size = sf.stat().st_size
                typer.echo(f"  {sf.name}: {size} bytes")
    except Exception as e:
        typer.echo(f"Error running snapshot health check: {e}")


if __name__ == "__main__":
    app()