import pathlib
import re
from typing import List, Optional, Tuple


def search(pattern: str, files: Optional[List[str]] = None, max_hits: int = 50) -> List[Tuple[str, int, str]]:
    """Search for pattern in files and return matches as (file, line_no, line_text)."""
    results = []

    if files is None:
        # Default to searching Python files in src directory
        src_path = pathlib.Path("src")
        if src_path.exists():
            files = [str(p) for p in src_path.rglob("*.py")]
        else:
            files = []

    compiled_pattern = re.compile(pattern)

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if compiled_pattern.search(line):
                        results.append((file_path, line_no, line.rstrip()))
                        if len(results) >= max_hits:
                            return results
        except Exception:
            # Skip files that can't be read
            continue

    return results


def create_ticket_from_match(file_path: str, line_no: int, line_text: str, note: str = "") -> str:
    """Create a coder ticket from a search match."""
    import datetime
    import json
    from pathlib import Path

    # Create ticket ID based on timestamp
    tid = f"cod_{int(datetime.datetime.utcnow().timestamp())}_{file_path.replace('/', '_').replace('.', '_')}_{line_no}"

    # Create the ticket data
    data = {
        "id": tid,
        "file": file_path,
        "lines": f"{line_no}",
        "note": f"{note} - Found via search: {line_text.strip()}",
        "done": False,
        "created": datetime.datetime.utcnow().isoformat(),
    }

    # Create the tickets directory if it doesn't exist
    tickets_dir = Path(".xsarena") / "coder" / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)

    # Write the ticket file
    ticket_file = tickets_dir / f"{tid}.json"
    ticket_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return tid


def search_and_create_tickets(pattern: str, note: str = "", files: Optional[List[str]] = None, max_hits: int = 50):
    """Search for pattern and create tickets for all matches."""
    matches = search(pattern, files, max_hits)
    ticket_ids = []

    for file_path, line_no, line_text in matches:
        ticket_id = create_ticket_from_match(file_path, line_no, line_text, note)
        ticket_ids.append(ticket_id)

    return ticket_ids
