from __future__ import annotations
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import typer
import yaml

app = typer.Typer(help="Cleanup utilities (TTL-based sweeper for ephemeral artifacts)")

HEADER_RX = re.compile(r"XSA-EPHEMERAL.*?ttl=(\d+)([dh])", re.IGNORECASE)

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
def sweep(ttl_override: int = typer.Option(None, "--ttl", help="Override TTL (days) for all matches"),
          apply: bool = typer.Option(False, "--apply/--dry", help="Apply deletions (default dry-run)"),
          verbose: bool = typer.Option(True, "--verbose/--quiet", help="Print actions")):
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
    for root in [Path(".xsarena/jobs"), Path("review"), Path("snapshot_chunks"), Path(".xsarena/tmp")]:
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
                        try:
                            d.rmdir()
                        except Exception:
                            pass

    typer.echo(f"Checked {total} file(s). Deleted {deleted}. Mode={'APPLY' if apply else 'DRY'}.")

@app.command("mark")
def mark_ephemeral(path: str, ttl: str = typer.Option("3d", "--ttl", help="TTL e.g., 3d or 72h")):
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
        header = f"# XSA-EPHEMERAL ttl={ttl}\n"
        p.write_text(header + txt, encoding="utf-8")
        typer.echo(f"Marked ephemeral → {p}")
    except Exception as e:
        typer.echo(f"Failed to mark: {e}")
        raise typer.Exit(1)