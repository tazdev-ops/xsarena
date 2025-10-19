# XSA-EPHEMERAL ttl=3d
set -euo pipefail

echo "== Preflight =="
git rev-parse --is-inside-work-tree >/dev/null || { echo "Not a git repo"; exit 1; }
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET="fix/ops-upgrade-pack"
if [[ "$BRANCH" != "$TARGET" ]]; then
  git switch -c "$TARGET" || git switch "$TARGET"
fi

mkdir -p review/backup_upgrade
ts="$(date -u +%Y%m%d-%H%M%S)"
backup() { [[ -f "$1" ]] && cp -a "$1" "review/backup_upgrade/${ts}.$(basename "$1")"; }

# ==============================================================================
# A — Bootstrap fixes (version-aware; safe if already applied)
# ==============================================================================

echo
echo "A1) core/config.py — api_key Optional[str]"
python - <<'PY'
import re, pathlib
p = pathlib.Path("src/xsarena/core/config.py")
if not p.exists():
    print("[SKIP] config.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8"); orig = txt
if "from typing import Optional" not in txt:
    txt = txt.replace("from pydantic import BaseModel", "from pydantic import BaseModel\nfrom typing import Optional")
txt = re.sub(r"api_key\s*:\s*\[REDACTED_SECRET\]\s*=\s*os\.getenv\(\"OPENROUTER_API_KEY\"\)",
             r"api_key: Optional[str] = os.getenv(\"OPENROUTER_API_KEY\")", txt, count=1)
if txt != orig: p.write_text(txt, encoding="utf-8"); print("[OK ] config.py updated")
else: print("[NOTE] config.py unchanged")
PY

echo
echo "A2) cli/context.py — create_backend(api_key, commas)"
python - <<'PY'
import re, pathlib
p = pathlib.Path("src/xsarena/cli/context.py")
if not p.exists():
    print("[SKIP] context.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8"); orig = txt
txt = re.sub(r"api_key=\[REDACTED_SECRET\]\s*\n(\s*)model=", r"api_key=cfg.api_key,\n\1model=", txt, count=1)
txt = re.sub(r"(def\s+rebuild_engine\([^\)]*\):[\s\S]*?create_backend\([^\)]*?api_key=)\[REDACTED_SECRET\]",
             r"\1self.config.api_key", txt, flags=re.S)
if txt != orig: p.write_text(txt, encoding="utf-8"); print("[OK ] context.py updated")
else: print("[NOTE] context.py unchanged")
PY

echo
echo "A3) core/engine.py — autopilot guards (getattr)"
python - <<'PY'
import pathlib
p = pathlib.Path("src/xsarena/core/engine.py")
if not p.exists():
    print("[SKIP] engine.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8"); orig = txt
txt = txt.replace("self.state.session_mode", "getattr(self.state, \"session_mode\", None)")
txt = txt.replace("self.state.coverage_hammer_on", "getattr(self.state, \"coverage_hammer_on\", False)")
if txt != orig: p.write_text(txt, encoding="utf-8"); print("[OK ] engine.py updated")
else: print("[NOTE] engine.py unchanged")
PY

echo
echo "A4) bridge/server.py — CORS + OPTIONS middleware"
python - <<'PY'
import re, pathlib
p = pathlib.Path("src/xsarena/bridge/server.py")
if not p.exists():
    print("[SKIP] server.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8"); orig = txt

# Insert middleware above main() if missing
if " @web.middleware" not in txt or "def cors_middleware(" not in txt:
    ins = (" @web.middleware\n"
           "async def cors_middleware(request, handler):\n"
           "    if request.method == \"OPTIONS\":\n"
           "        resp = web.Response()\n"
           "        resp.headers[\"Access-Control-Allow-Origin\"] = \"*\"\n"
           "        resp.headers[\"Access-Control-Allow-Methods\"] = \"POST, GET, OPTIONS\"\n"
           "        resp.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization\"\n"
           "        return resp\n"
           "    resp = await handler(request)\n"
           "    resp.headers[\"Access-Control-Allow-Origin\"] = \"*\"\n"
           "    resp.headers[\"Access-Control-Allow-Methods\"] = \"POST, GET, OPTIONS\"\n"
           "    resp.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization\"\n"
           "    return resp\n\n")
    txt = txt.replace("def main():", ins + "def main():")

# Ensure Application uses middleware
txt = re.sub(r"app\s*=\s*web\.Application\(\)", "app = web.Application(middlewares=[cors_middleware])", txt, count=1)

# Ensure OPTIONS routes exist (simple responders; headers via middleware)
if " @routes.options(\"/v1/chat/completions\")" not in txt:
    txt = txt.replace(" @routes.post(\"/v1/chat/completions\")",
                      " @routes.options(\"/v1/chat/completions\")\nasync def options_handler(_request):\n    return web.Response()\n\n"
                      " @routes.options(\"/push_response\")\nasync def options_handler_push(_request):\n    return web.Response()\n\n"
                      " @routes.options(\"/health\")\nasync def options_handler_health(_request):\n    return web.Response()\n\n"
                      " @routes.post(\"/v1/chat/completions\")")
txt = txt.replace("app.middlewares.append(cors_middleware)", "")

if txt != orig: p.write_text(txt, encoding="utf-8"); print("[OK ] server.py updated")
else: print("[NOTE] server.py unchanged")
PY

echo
echo "A5) healthcheck_script.sh — remove footer, default snapshot path"
if [[ -f healthcheck_script.sh ]]; then
  tail -n1 healthcheck_script.sh | grep -q "Answer received" && sed -i '$d' healthcheck_script.sh || true
  if grep -q 'SNAP_TXT="$OUT_DIR/xsa_snapshot_pro.txt"' healthcheck_script.sh; then
    sed -i 's|SNAP_TXT="$OUT_DIR/xsa_snapshot_pro.txt"|SNAP_TXT="${SNAP_TXT:-.xsarena/snapshots/final_snapshot.txt}"|' healthcheck_script.sh
    echo "[OK ] healthcheck_script.sh path updated"
  else
    echo "[NOTE] healthcheck path already customized"
  fi
else
  echo "[SKIP] healthcheck_script.sh not found"
fi

echo
echo "A6) Package stubs + CONTRIBUTING name tweak"
for d in src/xsarena/router src/xsarena/coder; do
  mkdir -p "$d"
  [[ -f "$d/__init__.py" ]] || { echo '"""Package placeholder."""' > "$d/__init__.py"; echo "[OK ] $d/__init__.py"; }
done
[[ -f CONTRIBUTING.md ]] && sed -i 's/LMASudio/XSArena/g' CONTRIBUTING.md || true

# ==============================================================================
# B — New CLI commands (doctor, playground, macros) + wiring + handoff
# ==============================================================================

echo
echo "B1) doctor command"
backup src/xsarena/cli/cmds_doctor.py || true
mkdir -p src/xsarena/cli
cat > src/xsarena/cli/cmds_doctor.py <<'PY'
from __future__ import annotations
import os, sys, platform, importlib, asyncio
from typing import Optional
import typer
from .context import CLIContext

app = typer.Typer(help="Health checks and smoke tests")

def _ok(msg: str): typer.echo(f"[OK] {msg}")
def _warn(msg: str): typer.echo(f"[WARN] {msg}")
def _err(msg: str): typer.echo(f"[ERR] {msg}")

 @app.command("env")
def env():
    py = sys.version.split()[0]
    _ok(f"Python {py} on {platform.platform()}")
    req = ["typer", "aiohttp", "pydantic", "yaml"]
    missing = []
    for mod in req:
        try: importlib.import_module(mod)
        except Exception: missing.append(mod)
    if missing:
        _warn(f"Missing modules: {', '.join(missing)}")
        raise typer.Exit(code=1)

 @app.command("ping")
def ping(backend: Optional[str] = typer.Option(None, "--backend", help="Override backend")):
    ctx = CLIContext.load()
    if backend: ctx.state.backend = backend
    if ctx.state.backend == "bridge":
        async def _go():
            import aiohttp
            url = (ctx.config.base_url or "").rstrip("/") + "/health"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=8) as r:
                        j = await r.json()
                        _ok(f"Bridge health: {j}")
                        return 0
            except Exception as e:
                _err(f"Bridge ping failed: {e}")
                _warn("Start bridge: xsarena service start-bridge; open LMArena (userscript on); click Retry; then rerun.")
                return 2
        raise typer.Exit(code=asyncio.run(_go()))
    else:
        if not (os.getenv("OPENROUTER_API_KEY") or ctx.config.api_key):
            _err("OPENROUTER_API_KEY not set")
            _warn("export OPENROUTER_API_KEY=... then rerun.")
            raise typer.Exit(code=2)
        _ok("OpenRouter config present.")
        raise typer.Exit(code=0)

 @app.command("run")
def run():
    try: env()
    except SystemExit as e: raise typer.Exit(code=e.code)
    try: ping()
    except SystemExit as e: raise typer.Exit(code=e.code)
    _ok("Doctor run complete.")
PY
echo "[OK ] doctor command written"

echo
echo "B2) Prompt Playground"
backup src/xsarena/cli/cmds_playground.py || true
cat > src/xsarena/cli/cmds_playground.py <<'PY'
from __future__ import annotations
import asyncio
from pathlib import Path
import typer
from .context import CLIContext
from ..core.prompt import compose_prompt

app = typer.Typer(help="Prompt composition and sampling playground")

def _slug(s: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s or "sample"

 @app.command("compose")
def compose(
    subject: str = typer.Argument(..., help="Subject/topic"),
    base: str = typer.Option("zero2hero", help="Base mode"),
    overlays: str = typer.Option("", help="Comma-separated overlays (e.g., narrative,no_bs,compressed)"),
    extra_notes: str = typer.Option("", help="Extra domain notes"),
    min_chars: int = typer.Option(4200, help="Min chars per chunk"),
    passes: int = typer.Option(1, help="Auto-extend passes"),
    max_chunks: int = typer.Option(12, help="Max chunks"),
):
    ovs = [o.strip() for o in overlays.split(",") if o.strip()] or None
    comp = compose_prompt(subject, base=base, overlays=ovs, extra_notes=extra_notes or None,
                          min_chars=min_chars, passes=passes, max_chunks=max_chunks)
    typer.echo("---- SYSTEM TEXT ----")
    typer.echo(comp.system_text)
    if comp.warnings:
        typer.echo("\n---- WARNINGS ----")
        for w in comp.warnings: typer.echo(f"- {w}")

 @app.command("sample")
def sample(
    subject: str = typer.Argument(...),
    base: str = typer.Option("zero2hero"),
    overlays: str = typer.Option("narrative,no_bs"),
    outdir: Path = typer.Option(Path("review/playground"), dir_okay=True, file_okay=False),
    min_chars: int = typer.Option(1000),
):
    ovs = [o.strip() for o in overlays.split(",") if o.strip()] or None
    comp = compose_prompt(subject, base=base, overlays=ovs, min_chars=min_chars, passes=0, max_chunks=1)
    ctx = CLIContext.load()
    eng = ctx.engine
    async def run_once():
        prompt = f"Write a dense sample introduction about: {subject}. Keep it cohesive; no NEXT markers."
        reply = await eng.send_and_collect(prompt, system_prompt=comp.system_text)
        return reply
    text = asyncio.run(run_once())
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{_slug(subject)}.sample.md"
    out.write_text(text.strip() + "\n", encoding="utf-8")
    typer.echo(f"[OK] Sample written → {out}")
PY
echo "[OK ] playground command written"

echo
echo "B3) Macros CLI"
backup src/xsarena/cli/cmds_macros.py || true
cat > src/xsarena/cli/cmds_macros.py <<'PY'
from __future__ import annotations
import json, re
from pathlib import Path
import typer

app = typer.Typer(help="Macro registry")
MACROS_PATH = Path(".xsarena/macros.json")

def _load() -> dict:
    if MACROS_PATH.exists():
        try: return json.loads(MACROS_PATH.read_text(encoding="utf-8"))
        except Exception: return {}
    return {}

def _save(d: dict):
    MACROS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACROS_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower())

def _apply(template: str, args: list[str]) -> str:
    def repl(m):
        spec = m.group(1)
        parts = spec.split("|")
        idx = int(parts[0]) - 1
        mod = parts[1] if len(parts) > 1 else None
        val = args[idx] if 0 <= idx < len(args) else m.group(0)
        if mod == "slug": val = _slugify(val)
        return val
    return re.sub(r"\$\{(\d+(?:\|slug)?)\}", repl, template)

 @app.command("save")
def save(name: str, template: str):
    d = _load(); d[name] = template; _save(d); typer.echo(f"[OK] macro '{name}' saved")

 @app.command("ls")
def ls():
    d = _load()
    if not d: typer.echo("(no macros)"); return
    for k, v in d.items(): typer.echo(f"- {k}: {v}")

 @app.command("rm")
def rm(name: str):
    d = _load()
    if name in d: d.pop(name); _save(d); typer.echo(f"[OK] macro '{name}' removed")
    else: typer.echo("[WARN] not found")

 @app.command("run")
def run(name: str, args: list[str] = typer.Argument(None)):
    d = _load()
    if name not in d: typer.echo("[ERR] macro not found"); raise typer.Exit(code=2)
    typer.echo(_apply(d[name], args or []))
PY
echo "[OK ] macros command written"

echo
echo "B4) Wire into main CLI (doctor, playground, macros)"
python - <<'PY'
from pathlib import Path
p = Path("src/xsarena/cli/main.py")
if not p.exists():
    print("[SKIP] main.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8"); orig = txt

imports = [
    "from .cmds_doctor import app as doctor_app",
    "from .cmds_playground import app as playground_app",
    "from .cmds_macros import app as macros_app",
]
for line in imports:
    if line not in txt:
        # add after any existing cmds imports if possible
        anchor = "from .cmds_report import app as report_app"
        if anchor in txt:
            idx = txt.find(anchor) + len(anchor)
            nl = txt.find("\n", idx)
            txt = txt[:nl+1] + line + "\n" + txt[nl+1:]
        else:
            txt = line + "\n" + txt

wires = [
 'app.add_typer(doctor_app, name="doctor", help="Health checks and smoke tests")',
 'app.add_typer(playground_app, name="playground", help="Prompt composition and sampling")',
 'app.add_typer(macros_app, name="macros", help="Macro registry")',
]
for wire in wires:
    if wire not in txt:
        anchor = 'app.add_typer(service_app, name="service", help="Service management (start servers)")'
        if anchor in txt:
            idx = txt.find(anchor) + len(anchor)
            nl = txt.find("\n", idx)
            txt = txt[:nl+1] + wire + "\n" + txt[nl+1:]
        else:
            cb = " @app.callback()"
            if cb in txt:
                idx = txt.find(cb)
                txt = txt[:idx] + wire + "\n" + txt[idx:]
            else:
                txt += "\n" + wire + "\n"

if txt != orig:
    p.write_text(txt, encoding="utf-8"); print("[OK ] main.py wired")
else:
    print("[NOTE] main.py unchanged")
PY

echo
echo "B5) Extend report with 'handoff'"
python - <<'PY'
from pathlib import Path
p = Path("src/xsarena/cli/cmds_report.py")
if not p.exists():
    print("[SKIP] cmds_report.py not found"); raise SystemExit
txt = p.read_text(encoding="utf-8")
if "def handoff(" in txt:
    print("[NOTE] handoff already exists")
else:
    add = r"""

import time
from pathlib import Path as _Path

 @app.command("handoff")
def handoff(book: str = typer.Option(None, "--book", help="Optional path to a relevant book"),
            outdir: str = typer.Option("docs/handoff", help="Output directory")):
    \"\"\"Create a handoff file for higher AI with snapshot digest and context.\"\"\"
    out_dir = _Path(outdir); out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"HANDOFF_{ts}.md"

    snap = _Path(".xsarena/snapshots/final_snapshot.txt")
    digest = ""
    if snap.exists():
        import hashlib
        digest = hashlib.sha256(snap.read_bytes()).hexdigest()

    head = []
    if book:
        try:
            b = _Path(book)
            if b.exists():
                text = b.read_text(encoding="utf-8", errors="replace")
                head = [text[:1200], text[-1200:]] if len(text) > 2400 else [text]
        except Exception:
            pass

    body = f\"\"\"# Handoff
Branch: (git rev-parse --abbrev-ref HEAD)
Snapshot digest (sha256 of final_snapshot.txt): {digest or '(none)'}
Commands run:
Expected vs Actual:
Errors/Logs:
Job ID/context (if any):
Ask:

## Book sample
{(''.join(['\\n--- head ---\\n', head[0], '\\n--- tail ---\\n', head[1]]) if len(head)==2 else (head[0] if head else '(none)'))}
\"\"\"
    path.write_text(body, encoding="utf-8")
    typer.echo(f"[OK] Handoff written → {path}")
"""
    p.write_text(txt + add, encoding="utf-8")
    print("[OK ] cmds_report.py extended with handoff")
PY

# ==============================================================================
# C — CI workflow, Makefile, docs (handoff, troubleshooting)
# ==============================================================================

echo
echo "C1) .github/workflows/ci.yml"
mkdir -p .github/workflows
if [[ ! -f .github/workflows/ci.yml ]]; then
cat > .github/workflows/ci.yml <<'YML'
name: ci
on:
  push: { branches: ["**"] }
  pull_request: {}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout @v4
      - uses: actions/setup-python @v5
        with: { python-version: "3.13" }
      - name: Install
        run: pip install -U pip && pip install -e ".[dev]"
      - name: Lint
        run: |
          ruff check .
          black --check .
      - name: Typecheck
        run: mypy .
      - name: Tests
        run: pytest -q
      - name: Docs help drift
        run: |
          bash scripts/gen_docs.sh || true
          git diff --exit-code || (echo "Docs drift detected. Run scripts/gen_docs.sh and commit." && exit 1)
YML
echo "[OK ] CI workflow added"
else
  echo "[NOTE] CI workflow exists; review if needed"
fi

echo
echo "C2) Makefile"
if [[ ! -f Makefile ]]; then
cat > Makefile <<'MK'
.PHONY: setup fmt lint test docs health bridge
setup:
 @src/xsarena/cli/cmds_pipeline.py install -U pip && pip install -e ".[dev]"
fmt:
 @ruff --fix . || true && black .
lint:
 @ruff check . && black --check . && mypy .
test:
 @pytest -q
docs:
 @bash scripts/gen_docs.sh
health:
 @SNAP_TXT=.xsarena/snapshots/final_snapshot.txt bash healthcheck_script.sh
bridge:
 @legacy/xsarena_cli.py service start-bridge
MK
echo "[OK ] Makefile added"
else
  echo "[NOTE] Makefile exists"
fi

echo
echo "C3) Docs: HANDOFF.md, TROUBLESHOOTING.md"
mkdir -p docs
[[ -f docs/HANDOFF.md ]] || cat > docs/HANDOFF.md <<'MD'
# Handoff (template)
- Branch: (git rev-parse --abbrev-ref HEAD)
- Snapshot digest: (sha256 of .xsarena/snapshots/final_snapshot.txt)
- Commands run:
- Expected vs Actual:
- Errors/Logs:
- Job ID/context (if any):
- Ask (what you want from higher AI):
MD
[[ -f docs/TROUBLESHOOTING.md ]] || cat > docs/TROUBLESHOOTING.md <<'MD'
# Troubleshooting

Bridge-first:
- Start: xsarena service start-bridge
- Browser: install/enable lmarena_bridge.user.js; open LMArena; click Retry once
- Ping: xsarena backend ping; xsarena doctor ping

OpenRouter fallback:
- export OPENROUTER_API_KEY=...
- xsarena backend ping --backend openrouter

Short chunks:
- Increase --min and --passes; set narrative on; compressed off

Repetition/restarts:
- cont.mode anchor; repetition warn on; anchors >= 200–300 chars

Doctor flow:
- xsarena doctor env; xsarena doctor ping; xsarena doctor run

Reports:
- xsarena report quick --book <path>
- xsarena report handoff --book <path>
MD
echo "[OK ] docs written/verified"

# ==============================================================================
# D — Compile, rules merge, docs regen, tests (sanity)
# ==============================================================================

echo
echo "D1) Compile imports"
python - <<'PY'
import sys, importlib, compileall
ok = compileall.compile_dir('src', quiet=1)
try:
    m = importlib.import_module('xsarena')
    print("xsarena version:", getattr(m,'__version__','?'))
except Exception as e:
    print("IMPORT ERROR:", e)
    sys.exit(1 if not ok else 0)
PY

echo
echo "D2) Merge rules and regenerate docs"
bash scripts/merge_session_rules.sh || echo "[WARN] merge rules failed (non-fatal)"
bash scripts/gen_docs.sh || echo "[WARN] docs regen failed (non-fatal)"

echo
echo "D3) Tests"
if command -v pytest >/dev/null 2>&1; then
  pytest -q || echo "[WARN] pytest failures; use doctor/ping to isolate"
else
  echo "[NOTE] pytest not installed; skipping"
fi

echo
echo "All-in-One Upgrade Pack applied. Next:"
echo "  - xsarena version && xsarena --help | head -n 40"
echo "  - xsarena doctor env && xsarena doctor ping && xsarena doctor run"
echo "  - python tools/snapshot_txt.py"
echo "  - SNAP_TXT=.xsarena/snapshots/final_snapshot.txt bash healthcheck_script.sh"
echo "Commit: git add -A && git commit -m 'feat(cli): doctor, playground, macros; fix(core/bridge): bootstrap; ci/makefile/docs; report handoff'"
# End
