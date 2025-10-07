import json
from pathlib import Path


def make_transplant_summary(job_id: str, jobs_dir: str = ".xsarena/jobs") -> str:
    """
    Create a transplant summary from a job's progress.
    Returns subject; last 3 completed (chapter:title); NEXT cursor.
    """
    job_dir = Path(jobs_dir) / job_id

    # Try to load plan.json to get detailed progress
    plan_path = job_dir / "plan.json"
    if plan_path.exists():
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)

            subject = plan_data.get("subject", "Unknown")
            completed_sections = plan_data.get("completed_sections", [])
            next_hint = plan_data.get("last_next", "Continue writing")

            # Get last few completed chapters/subtopics for context
            recent_progress = []
            if completed_sections:
                # Get last 3 completed sections/chapters for context
                for section_idx in completed_sections[-3:]:  # Get last 3 only
                    section_path = job_dir / f"section_{section_idx}.md"
                    if section_path.exists():
                        try:
                            with open(section_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                # Get a brief summary of the section content
                                lines = content.split("\n")
                                # Take first and last few lines as summary
                                summary = " ".join(lines[:3] + lines[-3:])[:200] + "..."
                                recent_progress.append(f"Section {section_idx}: {summary}")
                        except:
                            recent_progress.append(f"Section {section_idx}: Content summary unavailable")

            # Create transplant summary
            summary = f"Subject: {subject}\n"
            summary += f"Last 3 completed: {recent_progress[-3:] if recent_progress else ['None']}\n"
            summary += f"NEXT cursor: {next_hint}\n"
            summary += "Continue writing from this point with the same style, depth, and approach.\n"

            return summary
        except Exception:
            # Fallback if plan parsing fails
            pass

    # Fallback: use general method if plan.json is not available
    # Try to get section count by checking files
    import glob

    section_files = glob.glob(str(job_dir / "section_*.md"))
    section_count = len(section_files)

    # Attempt to extract subject from job.json if plan.json is not available
    try:
        with open(job_dir / "job.json", "r", encoding="utf-8") as f:
            job_data = json.load(f)
        subject = job_data.get("params", {}).get("subject", "Unknown")
    except:
        subject = "Unknown"

    summary = f"Subject: {subject}\n"
    summary += f"Completed sections: {section_count}\n"
    if section_count > 0:
        summary += f"Last completed: Section {section_count}\n"
    summary += "Continue from the next section with the same style and depth.\n"

    return summary
