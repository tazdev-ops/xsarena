"""Artifacts management for XSArena jobs."""

import os
from pathlib import Path
import json


def write_outline(job_id: str, outline_content: str) -> str:
    """Write outline to a file and return the path."""
    job_dir = Path(".xsarena") / "jobs" / job_id
    outline_path = job_dir / "outline.md"
    
    with open(outline_path, "w", encoding="utf-8") as f:
        f.write(f"# Outline for Job {job_id}\n\n{outline_content}")
    
    return str(outline_path)


def write_plan(job_id: str, plan_dict: dict) -> str:
    """Write plan to a file and return the path."""
    job_dir = Path(".xsarena") / "jobs" / job_id
    plan_path = job_dir / "plan.json"
    
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_dict, f, indent=2)
    
    return str(plan_path)


def write_aid(job_id: str, aid_type: str, content: str) -> str:
    """Write aid to a file and return the path."""
    job_dir = Path(".xsarena") / "jobs" / job_id
    aid_path = job_dir / f"{aid_type}.md"
    
    with open(aid_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(aid_path)