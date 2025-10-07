#!/usr/bin/env python3
import json
import pathlib
import sys

import typer

from ..core.quality import score_section

app = typer.Typer(help="Quality scoring and auto-rewrite")


def _jobs_root():
    return pathlib.Path(".xsarena") / "jobs"


@app.command("score")
def quality_score(job_id: str, threshold: float = 0.75):
    job_dir = _jobs_root() / job_id
    plan_path = job_dir / "plan.json"

    if not plan_path.exists():
        print(json.dumps({"error": f"Plan file not found for job {job_id}", "type": "error"}))
        return

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sections = []
    for ch in plan.get("chapters", []):
        for s in ch.get("subtopics", []):
            # Handle both 'file' and legacy numeric file naming
            file_key = s.get("file")
            if file_key:
                fp = job_dir / "sections" / file_key
            else:
                # Legacy approach - if no file key, skip or handle differently
                continue

            if fp.exists():
                text = fp.read_text(encoding="utf-8")
                score, breakdown = score_section(text)
                out = {
                    "chapter": ch["id"],
                    "section": s["id"],
                    "score": round(score, 3),
                    "breakdown": breakdown,
                    "file": str(fp),
                }
                print(json.dumps(out))
                sections.append(out)

    # summary
    scores = [x["score"] for x in sections]
    if scores:
        avg = sum(scores) / len(scores)
        print(json.dumps({"type": "summary", "avg": round(avg, 3), "below": sum(1 for x in scores if x < threshold)}))


@app.command("gate")
def quality_gate(job_id: str, threshold: float = 0.75, rewrite: bool = True):
    """Score all sections; auto-rewrite those below threshold using a small rubric overlay."""
    from ..core.backends import create_backend
    from ..core.engine import Engine
    from ..core.state import SessionState
    from ..core.templates import SYSTEM_PROMPTS

    plan_path = _jobs_root() / job_id / "plan.json"
    if not plan_path.exists():
        print(json.dumps({"error": f"Plan file not found for job {job_id}", "type": "error"}))
        return

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    job_json = _jobs_root() / job_id / "job.json"
    J = json.loads(job_json.read_text(encoding="utf-8")) if job_json.exists() else {}
    backend = J.get("backend") or "bridge"

    eng = Engine(create_backend(backend), SessionState())

    low = []
    for ch in plan.get("chapters", []):
        for s in ch.get("subtopics", []):
            file_key = s.get("file")
            if not file_key:
                continue
            fp = _jobs_root() / job_id / "sections" / file_key
            if not fp.exists():
                continue
            text = fp.read_text(encoding="utf-8")
            score, _ = score_section(text)
            if score < threshold:
                low.append((ch["id"], s["id"], fp, text, score))

    rubric_overlay = (
        "Rewrite this section to meet these gates:\n"
        "- Teach-before-use: define new terms at first mention (bold + 1 line).\n"
        "- Add 'Quick check' with 2–3 items; add 1–3 'Pitfalls'.\n"
        "- Smooth narrative (no bullet wall); end with NEXT: [...].\n"
        "Do not remove facts; preserve meaning.\n"
    )

    for ch_id, sec_id, fp, text, score in low:
        sys.stderr.write(f"[quality] rewriting {ch_id}:{sec_id} score={score:.2f}\n")
        sys_prompt = SYSTEM_PROMPTS["book"]  # reuse generic, then overlay
        user = rubric_overlay + "\n<<<SECTION\n" + text + "\nSECTION>>>"
        reply = eng.send_and_collect(user, system_prompt=sys_prompt)
        # Use your existing strip_next_marker helper if needed
        fp.write_text(reply, encoding="utf-8")

    print(json.dumps({"type": "gate", "rewritten": len(low), "threshold": threshold}))


@app.command("uniq")
def quality_uniqueness(job_id: str, n: int = 5, thresh: float = 0.22):
    from ..core.uniqlint import scan

    pairs = scan(job_id, n=n, thresh=thresh)
    for p in sorted(pairs, key=lambda x: -x["overlap"]):
        print(json.dumps(p))
    print(json.dumps({"type": "summary", "pairs": len(pairs), "threshold": thresh}))
