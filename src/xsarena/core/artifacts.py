import os
from typing import Any, Dict


def write_outline(job_id: str, text: str) -> str:
    """Write outline to file and return path"""
    job_dir = os.path.join(".xsarena", "jobs", job_id)
    outline_path = os.path.join(job_dir, "outline.md")

    with open(outline_path, "w", encoding="utf-8") as f:
        f.write(text)

    return outline_path


def write_plan(job_id: str, plan_dict: Dict[str, Any]) -> str:
    """Write plan to file and return path"""
    import json

    job_dir = os.path.join(".xsarena", "jobs", job_id)
    plan_path = os.path.join(job_dir, "plan.json")

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_dict, f, indent=2)

    return plan_path


def write_section(job_id: str, n: int, text: str) -> str:
    """Write section to file and return path"""
    job_dir = os.path.join(".xsarena", "jobs", job_id)
    section_path = os.path.join(job_dir, f"section_{n}.md")

    with open(section_path, "w", encoding="utf-8") as f:
        f.write(text)

    return section_path


def combine_sections(job_id: str) -> str:
    """Combine all sections into a final book and return path"""
    import glob

    job_dir = os.path.join(".xsarena", "jobs", job_id)
    section_files = sorted(glob.glob(os.path.join(job_dir, "section_*.md")))

    combined_content = ""
    for section_file in section_files:
        with open(section_file, "r", encoding="utf-8") as f:
            combined_content += f.read() + "\n\n"

    final_path = os.path.join(job_dir, "book.final.md")
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(combined_content)

    return final_path


def write_aid(job_id: str, kind: str, text: str) -> str:
    """Write study aid to file and return path"""
    job_dir = os.path.join(".xsarena", "jobs", job_id)
    aid_path = os.path.join(job_dir, f"book.{kind}.md")

    with open(aid_path, "w", encoding="utf-8") as f:
        f.write(text)

    return aid_path
