def approx_tokens(s: str) -> int:
    """Approximate token count by dividing character count by 4"""
    return (len(s) + 3) // 4


def analyze_events_for_adaptation(job_id: str, current_target: int) -> int:
    """
    Analyze events.jsonl to adjust target_chars based on observed tokens per chunk
    """
    import json
    from pathlib import Path

    events_path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not events_path.exists():
        return current_target

    observed_chars = []
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        if event.get("type") == "chunk_done" and "chars" in event:
                            observed_chars.append(event["chars"])
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass  # If we can't read the file, return original target

    if not observed_chars:
        return current_target

    # Calculate average observed chars
    avg_observed = sum(observed_chars) / len(observed_chars)

    # Adjust current target by ±10-15% to approach ~3000 chars
    target_optimal = 3000  # desired target
    adjustment_factor = (target_optimal / avg_observed) if avg_observed > 0 else 1.0

    # Limit adjustment to ±15% to prevent extreme swings
    adjustment_factor = max(0.85, min(1.15, adjustment_factor))

    new_target = int(current_target * adjustment_factor)

    # Ensure within reasonable bounds
    return max(1600, min(5200, new_target))


def analyze_events_for_adaptation(job_id: str, current_target: int) -> int:
    """
    Analyze events.jsonl to adjust target_chars based on observed tokens per chunk
    """
    import json
    from pathlib import Path

    events_path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not events_path.exists():
        return current_target

    observed_chars = []
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        if event.get("type") == "chunk_done" and "chars" in event:
                            observed_chars.append(event["chars"])
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass  # If we can't read the file, return original target

    if not observed_chars:
        return current_target

    # Calculate average observed chars
    avg_observed = sum(observed_chars) / len(observed_chars)

    # Adjust current target by ±10-15% to approach ~3000 chars
    target_optimal = 3000  # desired target
    adjustment_factor = (target_optimal / avg_observed) if avg_observed > 0 else 1.0

    # Limit adjustment to ±15% to prevent extreme swings
    adjustment_factor = max(0.85, min(1.15, adjustment_factor))

    new_target = int(current_target * adjustment_factor)

    # Ensure within reasonable bounds
    return max(1600, min(5200, new_target))


def parse_outline(outline_text: str, subject: str) -> dict:
    """
    Parse an outline text and return a structured plan.
    Supports both "1. Title" and "Chapter 1 — Title" formats.
    """
    import re

    lines = outline_text.split("\n")

    chapters = []
    chapter_idx = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match different chapter formats: "1. Title", "Chapter 1 — Title", etc.
        # Format 1: "1. Title" or "1) Title"
        match1 = re.match(r"^(\d+)[.\)]\s+(.+)$", line)
        # Format 2: "Chapter 1 — Title" or "Chapter 1: Title"
        match2 = re.match(r"^[Cc]hapter\s+(\d+)\s*[-:—]\s*(.+)$", line)
        # Format 3: just "Title" as continuation (if no number)
        title_match = re.match(r"^(\w.+)$", line)

        if match1:
            chapter_idx += 1
            # Check for subtopics in the same line or following lines
            subtopics = []
            title = match1.group(2).strip()
            # Look for bullet points or numbered subtopics in the same line or following
            # For now, we'll just use the title and add a placeholder subtopic
            if "introduction" in title.lower() or "overview" in title.lower():
                subtopics = ["Historical Context", "Key Concepts", "Foundations"]
            elif "principles" in title.lower() or "theory" in title.lower():
                subtopics = ["Fundamental Theories", "Core Principles", "Applications"]
            elif "advanced" in title.lower() or "modern" in title.lower():
                subtopics = ["Current Research", "Innovations", "Future Directions"]
            else:
                subtopics = [f"Key Subtopic for {title}", "Practical Applications", "Challenges & Considerations"]

            chapters.append({"n": int(match1.group(1)), "title": title, "subtopics": subtopics, "status": "pending"})
        elif match2:
            chapter_idx += 1
            subtopics = []
            title = match2.group(2).strip()
            # Add default subtopics based on title
            if "introduction" in title.lower() or "overview" in title.lower():
                subtopics = ["Historical Context", "Key Concepts", "Foundations"]
            elif "principles" in title.lower() or "theory" in title.lower():
                subtopics = ["Fundamental Theories", "Core Principles", "Applications"]
            elif "advanced" in title.lower() or "modern" in title.lower():
                subtopics = ["Current Research", "Innovations", "Future Directions"]
            else:
                subtopics = [f"Key Subtopic for {title}", "Practical Applications", "Challenges & Considerations"]

            chapters.append({"n": int(match2.group(1)), "title": title, "subtopics": subtopics, "status": "pending"})
        elif title_match and not match1 and not match2:
            # This might be a chapter without number
            chapter_idx += 1
            title = title_match.group(1).strip()
            subtopics = [f"Overview of {title}", f"Key aspects of {title}", f"Applications of {title}"]

            chapters.append({"n": chapter_idx, "title": title, "subtopics": subtopics, "status": "pending"})

    # Ensure at least one subtopic per chapter if none found
    for chapter in chapters:
        if not chapter.get("subtopics") or len(chapter["subtopics"]) == 0:
            chapter["subtopics"] = [
                f"Introduction to {chapter['title']}",
                f"Key concepts in {chapter['title']}",
                f"Applications of {chapter['title']}",
            ]

    # If no chapters were found, create a default structure
    if not chapters:
        chapters = [
            {
                "n": 1,
                "title": f"Chapter 1: Introduction to {subject}",
                "subtopics": ["Overview", "Historical Context", "Key Concepts"],
                "status": "pending",
            },
            {
                "n": 2,
                "title": "Chapter 2: Core Principles",
                "subtopics": ["Fundamental Theories", "Modern Applications", "Challenges"],
                "status": "pending",
            },
            {
                "n": 3,
                "title": "Chapter 3: Advanced Topics",
                "subtopics": ["Current Research", "Innovations", "Future Directions"],
                "status": "pending",
            },
        ]

    return {"subject": subject, "chapters": chapters, "last_next": "Begin the introduction", "completed_sections": []}


def target_chars(
    system_text: str, anchor: str, window_tokens: int = 8000, job_id: str = None, current_target: int = None
) -> int:
    """Calculate target character length for a chunk based on token budget"""
    s = approx_tokens(system_text or "")
    a = approx_tokens(anchor or "")
    usable = max(0, window_tokens - s - a)
    chars = int(usable * 4 * 0.65)  # 65% margin
    base_target = max(1600, min(5200, chars))

    # Apply adaptive adjustment if job_id is provided
    if job_id is not None:
        return analyze_events_for_adaptation(job_id, base_target)
    elif current_target is not None:
        return analyze_events_for_adaptation(
            "temp", current_target
        )  # for cases where we have a current target but no job_id
    else:
        return base_target


def pick_anchor(prev_text: str, anchor_len: int = 200) -> str:
    """Pick an anchor from the end of the previous text, cutting at sentence boundaries"""
    if not prev_text:
        return ""

    s = prev_text[-anchor_len:]
    # cut to last sentence boundary
    for ch in (".", "!", "?"):
        p = s.rfind(ch)
        if p != -1 and p >= len(s) - 120:
            s = s[: p + 1]
            break
    return s.strip()
