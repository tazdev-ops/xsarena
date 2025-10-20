#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(".").resolve()
Q_PATH = ROOT / ".xsarena" / "ops" / "c2_queue.json"
S_PATH = ROOT / ".xsarena" / "ops" / "c2_status.json"
REPORT_DIR = ROOT / "review" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_ENV = os.environ.copy()
DEFAULT_ENV["NO_COLOR"] = "1"
DEFAULT_ENV["RICH_NO_COLOR"] = "1"


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def run_cmd(args: List[str]) -> Dict:
    """Run a command safely (no shell=True)."""
    try:
        cp = subprocess.run(
            args,
            env=DEFAULT_ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {"code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    except Exception as e:
        return {"code": -1, "stdout": "", "stderr": str(e)}


def write_report(name_hint: str, content: str, out_file: str | None) -> str:
    if out_file:
        p = ROOT / out_file
    else:
        p = REPORT_DIR / f"{name_hint}_{int(time.time())}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p.relative_to(ROOT))


def task_project_map(task) -> Dict:
    lines = []
    for base in [
        ROOT / "src",
        ROOT / "docs",
        ROOT / "directives",
        ROOT / "tools",
        ROOT / "data",
        ROOT / ".xsarena",
    ]:
        if base.exists():
            lines.append(f"## {base.relative_to(ROOT)}/\n")
            for path in sorted(base.rglob("*")):
                rel = str(path.relative_to(ROOT))
                depth = rel.count(os.sep)
                name = path.name + ("/" if path.is_dir() else "")
                lines.append("  " * depth + f"- {name}")
            lines.append("")
    rep = "# Project Map\n\n" + "\n".join(lines) if lines else "# Project Map\n\n(none)"
    out = write_report("PROJECT_MAP", rep, task.get("out_file"))
    return {"ok": True, "report": out}


def task_commands_index(task) -> Dict:
    # Build a quick index from top-level help and group helps
    out_lines = ["# Commands Index\n"]
    r = run_cmd(["xsarena", "--help"])
    out_lines += ["## xsarena --help", "```", r["stdout"].strip(), "```", ""]
    # Try known groups
    groups = [
        "run",
        "author",
        "analyze",
        "study",
        "dev",
        "ops",
        "utils",
        "settings",
        "interactive",
        "docs",
    ]
    for g in groups:
        r2 = run_cmd(["xsarena", g, "--help"])
        if r2["code"] == 0 and r2["stdout"].strip():
            out_lines += [
                f"## xsarena {g} --help",
                "```",
                r2["stdout"].strip(),
                "```",
                "",
            ]
    out = write_report("COMMANDS_INDEX", "\n".join(out_lines), task.get("out_file"))
    return {"ok": True, "report": out}


def task_snapshot_preflight_verify(task) -> Dict:
    # Params: mode, policy, max_per_file, total_max, disallow (list), fail_on (list), require (list)
    params = task.get("params", {})
    cmd = [
        "xsarena",
        "ops",
        "snapshot",
        "verify",
        "--mode",
        params.get("mode", "minimal"),
    ]
    if params.get("policy"):
        cmd += ["--policy", params["policy"]]
    for d in params.get("disallow", []):
        cmd += ["--disallow", d]
    for r in params.get("require", []):
        cmd += ["--require", r]
    for f in params.get("fail_on", []):
        cmd += ["--fail-on", f]
    if "max_per_file" in params:
        cmd += ["--max-per-file", str(params["max_per_file"])]
    if "total_max" in params:
        cmd += ["--total-max", str(params["total_max"])]
    r = run_cmd(cmd)
    rep = f"# Snapshot Preflight Verify\n\nCommand:\n```\n{' '.join(cmd)}\n```\n\nExit: {r['code']}\n\nStdout:\n```\n{r['stdout']}\n```\n\nStderr:\n```\n{r['stderr']}\n```"
    out = write_report("SNAPSHOT_PREFLIGHT", rep, task.get("out_file"))
    return {"ok": r["code"] == 0, "report": out}


def task_snapshot_postflight_verify(task) -> Dict:
    # Params: file, max_per_file, disallow, fail_on, redaction_expected
    params = task.get("params", {})
    snap = params.get("file", "repo_flat.txt")
    cmd = ["xsarena", "ops", "snapshot", "verify", "--file", snap]
    if "max_per_file" in params:
        cmd += ["--max-per-file", str(params["max_per_file"])]
    for d in params.get("disallow", []):
        cmd += ["--disallow", d]
    for f in params.get("fail_on", []):
        cmd += ["--fail-on", f]
    if params.get("redaction_expected"):
        cmd += ["--redaction-expected"]
    r = run_cmd(cmd)
    rep = f"# Snapshot Postflight Verify\n\nCommand:\n```\n{' '.join(cmd)}\n```\n\nExit: {r['code']}\n\nStdout:\n```\n{r['stdout']}\n```\n\nStderr:\n```\n{r['stderr']}\n```"
    out = write_report("SNAPSHOT_POSTFLIGHT", rep, task.get("out_file"))
    return {"ok": r["code"] == 0, "report": out}


def task_smoke(task) -> Dict:
    script = (
        ROOT
        / "scripts"
        / ("smoke.ps1" if sys.platform.startswith("win") else "smoke.sh")
    )
    if not script.exists():
        return {
            "ok": False,
            "report": write_report(
                "SMOKE", "# Smoke script not found\n", task.get("out_file")
            ),
        }
    if sys.platform.startswith("win"):
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    else:
        cmd = [str(script)]
    r = run_cmd(cmd)
    rep = f"# Smoke\n\nExit: {r['code']}\n\nStdout:\n```\n{r['stdout']}\n```\n\nStderr:\n```\n{r['stderr']}\n```"
    out = write_report("SMOKE", rep, task.get("out_file"))
    return {"ok": r["code"] == 0, "report": out}


def task_jobs_report(task) -> Dict:
    r1 = run_cmd(["xsarena", "ops", "jobs", "ls"])
    rep = ["# Jobs Report\n", "## jobs ls\n", "```\n", r1["stdout"].strip(), "\n```\n"]
    out = write_report("JOBS", "\n".join(rep), task.get("out_file"))
    return {"ok": r1["code"] == 0, "report": out}


def task_config_show(task) -> Dict:
    r1 = run_cmd(["xsarena", "settings", "show"])
    r2 = run_cmd(["xsarena", "ops", "config", "config-check"])
    rep = f"# Settings\n\n## settings show\n```\n{r1['stdout']}\n```\n\n## config-check\n```\n{r2['stdout']}\n```"
    out = write_report("SETTINGS", rep, task.get("out_file"))
    return {"ok": r1["code"] == 0 and r2["code"] == 0, "report": out}


def task_search_files(task) -> Dict:
    # Params: pattern (regex), root (dir), max_hits
    params = task.get("params", {})
    root = Path(params.get("root", "."))
    pat = re.compile(params.get("pattern", "."))
    max_hits = int(params.get("max_hits", 200))
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and p.stat().st_size < 1_000_000:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if pat.search(line):
                        hits.append(f"{p}:{i}: {line.strip()}")
                        if len(hits) >= max_hits:
                            break
            except Exception:
                continue
        if len(hits) >= max_hits:
            break
    rep = "# Search Results\n\n" + "\n".join(hits[:max_hits] or ["(none)"])
    out = write_report("SEARCH", rep, task.get("out_file"))
    return {"ok": True, "report": out}


TASKS = {
    "project_map": task_project_map,
    "commands_index": task_commands_index,
    "snapshot_preflight_verify": task_snapshot_preflight_verify,
    "snapshot_postflight_verify": task_snapshot_postflight_verify,
    "smoke": task_smoke,
    "jobs_report": task_jobs_report,
    "config_show": task_config_show,
    "search_files": task_search_files,
}


def process_once() -> Dict:
    q = read_json(Q_PATH, {"tasks": []})
    s = read_json(
        S_PATH,
        {"last_run_ts": None, "tasks_done": 0, "tasks_failed": 0, "last_reports": []},
    )
    reports = []
    done = 0
    failed = 0
    changed = False
    for t in q.get("tasks", []):
        if t.get("status", "pending") != "pending":
            continue
        t["status"] = "running"
        changed = True
        write_json(Q_PATH, q)

        fn = TASKS.get(t.get("type"))
        if not fn:
            t["status"] = "failed"
            t["result"] = {"error": f"unknown task type: {t.get('type')}"}
            failed += 1
            changed = True
            write_json(Q_PATH, q)
            continue

        try:
            res = fn(t)
            t["status"] = "done" if res.get("ok") else "failed"
            t["result"] = res
            if "report" in res:
                reports.append(res["report"])
            if t["status"] == "done":
                done += 1
            else:
                failed += 1
        except Exception as e:
            t["status"] = "failed"
            t["result"] = {"error": str(e)}
            failed += 1
        changed = True
        write_json(Q_PATH, q)

    if changed:
        s["last_run_ts"] = ts()
        s["tasks_done"] = s.get("tasks_done", 0) + done
        s["tasks_failed"] = s.get("tasks_failed", 0) + failed
        s["last_reports"] = reports or s.get("last_reports", [])
        write_json(S_PATH, s)

    return {"done": done, "failed": failed, "reports": reports}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=5)
    args = ap.parse_args()

    if args.once:
        res = process_once()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["failed"] == 0 else 1)

    if args.watch:
        while True:
            res = process_once()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
