from __future__ import annotations

import contextlib
import json
import subprocess
import time
from pathlib import Path

import typer
import yaml

app = typer.Typer(help="Startup reader: consults startup.yml and prints what was read")

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


def _load_yaml(p: Path) -> dict:
    try:
        return yaml.safe_load(_read(p)) or {}
    except Exception:
        return {}


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
    sh = Path("scripts/merge_session_rules.sh")
    if sh.exists():
        with contextlib.suppress(Exception):
            subprocess.run(["bash", str(sh)], check=False)


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
            '# CLI Agent Rules (Minimal)\n- xsarena fix run\n- xsarena run book "Subject"\n',
            encoding="utf-8",
        )
        _maybe_merge()
    typer.echo("[boot] init complete.")
