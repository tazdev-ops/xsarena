from __future__ import annotations

import json
import re
import subprocess
import time
from json import dumps, loads
from pathlib import Path
from typing import Dict, List

import typer

app = typer.Typer(help="Adaptive inspection and safe fixes (dry-run by default)")

OPS_POINTERS = Path(".xsarena/ops/pointers.json")


def _load_pointers() -> dict:
    if OPS_POINTERS.exists():
        try:
            return loads(OPS_POINTERS.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_pointers(d: dict):
    OPS_POINTERS.parent.mkdir(parents=True, exist_ok=True)
    OPS_POINTERS.write_text(dumps(d, indent=2), encoding="utf-8")


def _load_suppress() -> dict:
    p = _load_pointers()
    sup = p.get("suppress", {})
    for k in CHECKS:
        sup.setdefault(k, [])
    return sup


def _save_suppress(sup: dict):
    p = _load_pointers()
    p["suppress"] = sup
    _save_pointers(p)


def _apply_suppress(report: dict) -> dict:
    sup = _load_suppress()
    new = []
    for item in report.get("summary", []):
        chk = item.split(":")[0].strip() if ":" in item else ""
        if chk in sup:
            pats = sup.get(chk) or []
            if not pats:
                continue
            if any(pat.lower() in item.lower() for pat in pats):
                continue
        new.append(item)
    report["summary"] = new
    return report


CHECKS = ["branding", "dirs", "gitignore", "ephemeral", "helpdocs", "config", "wiring"]
GITIGNORE_LINES = [
    "snapshot_chunks/",
    "xsa_min_snapshot*.txt",
    "review/",
    ".xsarena/tmp/",
]
CONTENT_DIRS = ["books/finals", "books/outlines", "books/flashcards", "books/archive"]
HELP_TARGETS = [
    ("xsarena --help", "docs/_help_root.txt"),
    ("xsarena service --help", "docs/_help_serve.txt"),
    ("xsarena snapshot --help", "docs/_help_snapshot.txt"),
    ("xsarena jobs --help", "docs/_help_jobs.txt"),
    ("xsarena doctor --help", "docs/_help_doctor.txt"),
    ("xsarena book --help", "docs/_help_z2h.txt"),
]


def _ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _read(path: Path, max_bytes: int = 400_000) -> str:
    try:
        data = path.read_bytes()
    except Exception:
        return ""
    if len(data) > max_bytes:
        data = data[: max_bytes // 2] + b"\n---TRUNCATED---\n" + data[-max_bytes // 2 :]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_gitignore(lines: List[str]) -> List[str]:
    gi = Path(".gitignore")
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    added = []
    for ln in lines:
        if ln not in existing:
            existing.append(ln)
            added.append(ln)
    if added:
        _write(gi, "\n".join(existing) + "\n")
    return added


def _gen_help_file(cmd: str, dest: Path):
    try:
        out = subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.STDOUT
        )
        _write(dest, out)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.output


def _inspect() -> Dict:
    report: Dict = {"checks": {}, "summary": []}

    # branding drift in userscript
    us = Path("xsarena_bridge.user.js")
    branding = {"file": str(us), "needs_fix": False}
    if us.exists():
        txt = _read(us)
        if "LMASudio" in txt or "LMASudioBridge" in txt:
            branding["needs_fix"] = True
    report["checks"]["branding"] = branding
    if branding["needs_fix"]:
        report["summary"].append(
            "branding: userscript contains 'LMASudio' — suggest normalize to 'XSArena'"
        )

    # content dirs present
    missing_dirs = [d for d in CONTENT_DIRS if not Path(d).exists()]
    report["checks"]["dirs"] = {"missing": missing_dirs}
    if missing_dirs:
        report["summary"].append(f"dirs: creating {missing_dirs}")

    # .gitignore lines
    gi_missing = []
    gi = Path(".gitignore")
    gi_text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    for ln in GITIGNORE_LINES:
        if ln not in gi_text:
            gi_missing.append(ln)
    report["checks"]["gitignore"] = {"missing": gi_missing}
    if gi_missing:
        report["summary"].append(f"gitignore: add {gi_missing}")

    # ephemeral scripts in review/
    eph = []
    for p in Path("review").rglob("*.sh"):
        try:
            first = p.open("r", encoding="utf-8").readline()
        except Exception:
            first = ""
        if "XSA-EPHEMERAL" not in first:
            eph.append(str(p))
    report["checks"]["ephemeral"] = {"unmarked": eph}
    if eph:
        report["summary"].append(f"ephemeral: mark header on {len(eph)} review/*.sh")

    # help docs drift (presence only)
    help_missing = []
    for _cmd, dest in HELP_TARGETS:
        if not Path(dest).exists():
            help_missing.append(dest)
    report["checks"]["helpdocs"] = {"missing": help_missing}
    if help_missing:
        report["summary"].append(
            f"helpdocs: missing {help_missing} — regen via scripts/gen_docs.sh"
        )

    # config present and sane base_url
    cfg = Path(".xsarena/config.yml")
    conf = {"exists": cfg.exists(), "fixed_base_url": False}
    if cfg.exists():
        txt = _read(cfg)
        if "base_url:" in txt and "/v1" not in txt:
            conf["fixed_base_url"] = True
    report["checks"]["config"] = conf
    if not cfg.exists():
        report["summary"].append(
            "config: create .xsarena/config.yml (defaults; no secrets)"
        )
    elif conf["fixed_base_url"]:
        report["summary"].append("config: normalize base_url to end with /v1")

    # wiring (dynamic discovery): warn if cmds_*.py likely not registered in main.py
    main = Path("src/xsarena/cli/main.py")
    wiring = {"main_exists": main.exists(), "warn": []}
    if main.exists():
        mtxt = _read(main)
        # map cmds_foo.py → 'foo' (default convention)
        for p in Path("src/xsarena/cli").glob("cmds_*.py"):
            name = p.stem.replace("cmds_", "").replace("_", "-")
            # known aliases mapping (control-jobs vs control)
            expected = "control-jobs" if name == "control" else name
            if expected not in mtxt and name not in mtxt:
                wiring["warn"].append(f"main.py: '{name}' likely not registered")
    if wiring["warn"]:
        report["summary"].append("wiring: " + "; ".join(wiring["warn"]))
    report["checks"]["wiring"] = wiring

    return report


def _apply(report: Dict) -> Dict:
    actions = {"changed": [], "notes": []}

    # Add missing content dirs
    for d in report.get("checks", {}).get("dirs", {}).get("missing", []):
        Path(d).mkdir(parents=True, exist_ok=True)
        actions["changed"].append(f"mkdir {d}")

    # Add .gitignore lines
    need = report.get("checks", {}).get("gitignore", {}).get("missing", [])
    if need:
        added = _append_gitignore(need)
        if added:
            actions["changed"].append(f".gitignore +{added}")

    # Branding in userscript
    us = report.get("checks", {}).get("branding", {}).get("file")
    if us and report["checks"]["branding"]["needs_fix"]:
        p = Path(us)
        txt = _read(p)
        txt2 = txt.replace("LMASudio", "XSArena").replace(
            "LMASudioBridge", "XSArenaBridge"
        )
        if txt != txt2:
            _write(p, txt2)
            actions["changed"].append("xsarena_bridge.user.js branding normalized")

    # Create default config if missing
    cfg = Path(".xsarena/config.yml")
    if not cfg.exists():
        default = (
            "backend: bridge\nbase_url: http://127.0.0.1:5102/v1\nmodel: default\n"
        )
        _write(cfg, default)
        actions["changed"].append(".xsarena/config.yml created (defaults)")
    else:
        # normalize base_url to end with /v1 if needed
        txt = _read(cfg)
        if "base_url:" in txt and "/v1" not in txt:
            txt2 = re.sub(
                r"(base_url:\s*http[^\s/]+://[^\s]+?)(\s*$)",
                r"\1/v1\n",
                txt,
                flags=re.MULTILINE,
            )
            if txt2 != txt:
                _write(cfg, txt2)
                actions["changed"].append("config base_url normalized")

    # Mark unmarked ephemeral scripts
    for f in report.get("checks", {}).get("ephemeral", {}).get("unmarked", []):
        p = Path(f)
        try:
            body = p.read_text(encoding="utf-8", errors="ignore")
            if "XSA-EPHEMERAL" not in body.splitlines()[0]:
                p.write_text("# XSA-EPHEMERAL ttl=7d\n" + body, encoding="utf-8")
                actions["changed"].append(f"marked ephemeral: {f}")
        except Exception:
            pass

    return actions


@app.command("inspect")
def adapt_inspect(
    save: bool = typer.Option(True, "--save/--no-save", help="Write plan to review/")
):
    """Analyze repo state and write a plan (no changes)."""
    report = _inspect()
    report = _apply_suppress(report)  # NEW
    typer.echo(json.dumps(report["summary"], indent=2))
    if save:
        out = Path("review") / f"adapt_plan_{time.strftime('%Y%m%d-%H%M%S')}.json"
        _write(out, json.dumps(report, indent=2))
        typer.echo(f"[adapt] plan → {out}")


@app.command("fix")
def adapt_fix(
    apply: bool = typer.Option(
        False, "--apply/--dry", help="Apply safe fixes (default dry-run)"
    )
):
    """Apply safe, targeted fixes (no refactors)."""
    report = _inspect()
    if not apply:
        typer.echo("[adapt] DRY-RUN. Planned changes:")
        typer.echo(json.dumps(report["summary"], indent=2))
        return
    actions = _apply(report)
    typer.echo(json.dumps(actions, indent=2))
    # re-run minimal health
    typer.echo("[adapt] post-fix health:")
    try:
        subprocess.run(["xsarena", "fix", "run"], check=False)
        subprocess.run(["xsarena", "backend", "ping"], check=False)
        subprocess.run(["xsarena", "doctor", "run"], check=False)
    except Exception:
        pass


@app.command("plan")
def adapt_plan():
    """Alias to inspect (compat)."""
    adapt_inspect()


@app.command("suppress-add")
def suppress_add(
    check: str = typer.Argument(...), pattern: str = typer.Option("", "--pattern")
):
    if check not in CHECKS:
        typer.echo(f"Unknown check. Choose: {', '.join(CHECKS)}")
        raise typer.Exit(2)
    sup = _load_suppress()
    if pattern and pattern not in sup[check]:
        sup[check].append(pattern)
    if not pattern:
        sup[check] = []
    _save_suppress(sup)
    typer.echo(
        f"[adapt] suppression saved for '{check}' ({pattern if pattern else 'all'})"
    )


@app.command("suppress-ls")
def suppress_ls():
    typer.echo(json.dumps(_load_suppress(), indent=2))


@app.command("suppress-clear")
def suppress_clear(check: str = typer.Argument("all")):
    sup = _load_suppress()
    if check == "all":
        for k in CHECKS:
            sup[k] = []
    else:
        if check not in CHECKS:
            typer.echo(f"Unknown check. Choose: {', '.join(CHECKS)}")
            raise typer.Exit(2)
        sup[check] = []
    _save_suppress(sup)
    typer.echo("[adapt] suppression cleared")
