import datetime
import difflib
import json
import os
import pathlib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Ticket:
    id: str
    file: str
    lines: Optional[str]
    note: Optional[str]
    done: bool = False


class CoderSession:
    def __init__(self, root: str = "."):
        self.root = pathlib.Path(root).resolve()
        self.dir = self.root / ".xsarena" / "coder"
        (self.dir / "tickets").mkdir(parents=True, exist_ok=True)
        (self.dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.dir / "patches").mkdir(parents=True, exist_ok=True)

    def _wlog(self, msg: dict):
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
            msg["ts"] = datetime.datetime.utcnow().isoformat()
            f.write(json.dumps(msg) + "\n")

    def ticket_new(self, file: str, lines: Optional[str], note: Optional[str]) -> str:
        tid = f"cod_{int(datetime.datetime.utcnow().timestamp())}"
        data = {"id": tid, "file": file, "lines": lines, "note": note, "done": False}
        (self.dir / "tickets" / f"{tid}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._wlog({"type": "ticket_new", **data})
        return tid

    def ticket_next(self) -> Optional[Ticket]:
        """Get the next pending ticket."""
        tickets_dir = self.dir / "tickets"
        for ticket_file in tickets_dir.glob("*.json"):
            data = json.loads(ticket_file.read_text(encoding="utf-8"))
            if not data.get("done", False):
                return Ticket(
                    id=data["id"], file=data["file"], lines=data["lines"], note=data["note"], done=data["done"]
                )
        return None

    def ticket_list(self) -> List[Ticket]:
        """Get all tickets."""
        tickets = []
        tickets_dir = self.dir / "tickets"
        for ticket_file in tickets_dir.glob("*.json"):
            data = json.loads(ticket_file.read_text(encoding="utf-8"))
            tickets.append(
                Ticket(id=data["id"], file=data["file"], lines=data["lines"], note=data["note"], done=data["done"])
            )
        return tickets

    def _parse_unified_diff(self, diff_str: str) -> List[dict]:
        """Parse a unified diff string into hunks."""
        lines = diff_str.split("\n")
        hunks = []
        current_hunk = None

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("@@ "):
                # Parse hunk header @@ -old_start,old_count +new_start,new_count @@
                hunk_match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
                if hunk_match:
                    old_start = int(hunk_match.group(1))
                    old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                    new_start = int(hunk_match.group(3))
                    new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

                    current_hunk = {
                        "header": line,
                        "old_start": old_start,
                        "old_count": old_count,
                        "new_start": new_start,
                        "new_count": new_count,
                        "changes": [],
                    }
                    hunks.append(current_hunk)
            elif current_hunk and line.startswith(("+", "-", " ")):
                current_hunk["changes"].append(line)
            i += 1

        return hunks

    def patch_dry_run(self, ticket_id: str, diff_str: str) -> dict:
        """Dry run a patch to see if it would apply cleanly."""
        # Load the ticket to get the file path
        ticket_file = self.dir / "tickets" / f"{ticket_id}.json"
        if not ticket_file.exists():
            return {"error": "Ticket not found", "applied_hunks": 0}

        ticket_data = json.loads(ticket_file.read_text(encoding="utf-8"))
        file_path = self.root / ticket_data["file"]

        if not file_path.exists():
            return {"error": f"File not found: {file_path}", "applied_hunks": 0}

        # Create a temporary file with current content
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as tmp:
            tmp.write(file_path.read_text(encoding="utf-8"))
            tmp_path = tmp.name

        try:
            # Apply the diff to the temporary file using patch command
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".diff") as diff_tmp:
                diff_tmp.write(diff_str)
                diff_path = diff_tmp.name

            # Try to apply the patch in dry-run mode
            result = subprocess.run(
                ["patch", "-p0", "-f", "--dry-run", tmp_path, diff_path], capture_output=True, text=True, cwd=self.root
            )

            # Clean up temporary files
            os.unlink(diff_path)
            os.unlink(tmp_path)

            if result.returncode == 0:
                # Count hunks by parsing the diff
                hunks = self._parse_unified_diff(diff_str)
                return {"error": None, "applied_hunks": len(hunks)}
            else:
                return {"error": result.stderr, "applied_hunks": 0}
        except Exception as e:
            # Clean up in case of exception
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return {"error": str(e), "applied_hunks": 0}

    def patch_apply(self, ticket_id: str, diff_str: str) -> dict:
        """Apply a patch to the specified file."""
        # Load the ticket to get the file path
        ticket_file = self.dir / "tickets" / f"{ticket_id}.json"
        if not ticket_file.exists():
            return {"error": "Ticket not found", "applied_hunks": 0}

        ticket_data = json.loads(ticket_file.read_text(encoding="utf-8"))
        file_path = self.root / ticket_data["file"]

        if not file_path.exists():
            return {"error": f"File not found: {file_path}", "applied_hunks": 0}

        # Backup original file
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

        try:
            # Write the diff to a temporary file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".diff") as diff_tmp:
                diff_tmp.write(diff_str)
                diff_path = diff_tmp.name

            # Apply the patch
            result = subprocess.run(
                ["patch", "-p0", "-f", str(file_path), diff_path], capture_output=True, text=True, cwd=self.root
            )

            # Clean up diff file
            os.unlink(diff_path)

            if result.returncode == 0:
                # Count hunks by parsing the diff
                hunks = self._parse_unified_diff(diff_str)

                # Mark the ticket as done
                ticket_data["done"] = True
                ticket_file.write_text(json.dumps(ticket_data, indent=2), encoding="utf-8")

                # Log the event
                self._wlog(
                    {
                        "type": "patch_applied",
                        "ticket_id": ticket_id,
                        "file": str(file_path),
                        "applied_hunks": len(hunks),
                        "stdout": result.stdout,
                    }
                )

                return {"error": None, "applied_hunks": len(hunks)}
            else:
                # Restore backup
                file_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                backup_path.unlink()
                return {"error": result.stderr, "applied_hunks": 0}
        except Exception as e:
            # Restore backup on exception
            if backup_path.exists():
                file_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                backup_path.unlink()
            return {"error": str(e), "applied_hunks": 0}

    def run_tests(self, args: str = "-q") -> dict:
        """Run tests and return a summary."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest"] + args.split(), capture_output=True, text=True, cwd=self.root
            )

            # Parse the pytest output for a concise summary
            lines = result.stdout.split("\n")
            summary_line = next(
                (line for line in lines if "passed" in line or "failed" in line), "No test summary found"
            )

            return {
                "exit_code": result.returncode,
                "summary": summary_line.strip(),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as e:
            return {"exit_code": -1, "summary": f"Error running tests: {str(e)}", "stdout": "", "stderr": str(e)}

    def diff_file(self, file_path: str) -> str:
        """Get minimal diff for a file (<= 500 lines)."""
        try:
            file_path_full = self.root / file_path
            if not file_path_full.exists():
                return f"File not found: {file_path}"

            # Read the current file content
            current_content = file_path_full.read_text(encoding="utf-8")

            # Get the file as it was in the last committed state
            result = subprocess.run(["git", "show", f"HEAD:{file_path}"], capture_output=True, text=True, cwd=self.root)

            if result.returncode != 0:
                # If file wasn't in HEAD, return the full content as diff
                lines = current_content.split("\n")
                if len(lines) > 500:
                    lines = lines[:500] + ["... [truncated]"]
                return "\n".join([f"+ {line}" for line in lines])

            original_content = result.stdout

            # Generate diff
            original_lines = original_content.splitlines(keepends=True)
            current_lines = current_content.splitlines(keepends=True)

            diff = difflib.unified_diff(
                original_lines, current_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"
            )

            diff_lines = list(diff)
            if len(diff_lines) > 500:
                diff_lines = diff_lines[:500] + ["... [truncated]\n"]

            return "".join(diff_lines)

        except Exception as e:
            return f"Error getting diff: {str(e)}"
