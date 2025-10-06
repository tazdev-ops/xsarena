"""Simple pipeline runner for project playbooks (fix → test → format → commit)."""

import subprocess


def run_step(name: str, args: dict | None = None, apply: bool = False) -> dict:
    args = args or {}

    def _run(cmd: list[str]) -> dict:
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return {
                "ok": proc.returncode == 0,
                "code": proc.returncode,
                "stdout": (proc.stdout or "")[-8000:],
                "stderr": (proc.stderr or "")[-8000:],
            }
        except Exception as e:
            return {"ok": False, "code": -1, "stdout": "", "stderr": str(e)}

    if name == "ruff-fix":
        cmd = ["ruff", "check", ".", "--fix"]
        return {
            "name": name,
            "run": apply,
            "result": _run(cmd) if apply else {"ok": True},
        }
    if name == "black-format":
        cmd = ["black", "."]
        return {
            "name": name,
            "run": apply,
            "result": _run(cmd) if apply else {"ok": True},
        }
    if name == "pytest":
        cmd = ["pytest", "-q"]
        return {
            "name": name,
            "run": apply,
            "result": _run(cmd) if apply else {"ok": True},
        }
    if name == "git-commit":
        msg = args.get("message", "chore: pipeline commit")
        if not apply:
            return {"name": name, "run": False, "result": {"ok": True}}
        # add all and commit
        add = _run(["git", "add", "."])
        if not add.get("ok"):
            return {"name": name, "run": True, "result": add}
        return {"name": name, "run": True, "result": _run(["git", "commit", "-m", msg])}
    return {
        "name": name,
        "run": False,
        "result": {"ok": False, "stderr": f"unknown step: {name}"},
    }


def run_pipeline(steps: list[dict], apply: bool = False) -> list[dict]:
    results = []
    for st in steps:
        uses = st.get("uses")
        if not uses:
            results.append(
                {
                    "name": "(missing uses)",
                    "run": False,
                    "result": {"ok": False, "stderr": "missing uses"},
                }
            )
            continue
        results.append(run_step(uses, st.get("with"), apply=apply))
    return results
