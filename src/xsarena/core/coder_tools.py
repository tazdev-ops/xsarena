"""Additional coding tools for the agent that complement the existing file system tools."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tools import PathJail, apply_patch


class TicketManager:
    """Manages coding tickets for the agent."""

    def __init__(self, root_path: str = "./"):
        self.root_path = Path(root_path).resolve()
        self.tickets: List[Dict[str, Any]] = []
        self.path_jail = PathJail(str(self.root_path))

    def ticket_new(self, file: str, lines: str, note: str) -> str:
        """Create a new coding ticket."""
        ticket_id = str(uuid.uuid4())[:8]  # Short UUID
        ticket = {
            "id": ticket_id,
            "file": file,
            "lines": lines,
            "note": note,
            "created_at": self._now(),
            "status": "pending",
        }
        self.tickets.append(ticket)
        return ticket_id

    def ticket_next(self) -> Optional[Dict[str, Any]]:
        """Get the next pending ticket."""
        pending_tickets = [t for t in self.tickets if t["status"] == "pending"]
        if pending_tickets:
            return pending_tickets[0]
        return None

    def ticket_list(self) -> List[Dict[str, Any]]:
        """List all tickets."""
        return self.tickets.copy()

    def ticket_update(
        self, ticket_id: str, status: str = None, note: str = None
    ) -> bool:
        """Update a ticket's status or note."""
        for ticket in self.tickets:
            if ticket["id"] == ticket_id:
                if status:
                    ticket["status"] = status
                if note:
                    ticket["note"] = note
                return True
        return False

    def _now(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PatchManager:
    """Manages patch operations for the agent."""

    def __init__(self, root_path: str = "./"):
        self.root_path = Path(root_path).resolve()
        self.path_jail = PathJail(str(self.root_path))

    def patch_dry_run(self, filepath: str, patch_content: str) -> Dict[str, Any]:
        """Dry run a patch to see what would be changed."""
        try:
            # For now, we'll just validate that the patch is well-formed
            # In a real implementation, this would actually apply the patch in memory
            # and show the differences without modifying the file

            # Basic validation - check if patch content looks like a unified diff
            if not patch_content.strip().startswith(
                "--- "
            ) and not patch_content.strip().startswith("@@ "):
                return {
                    "error": "Patch content doesn't appear to be a valid unified diff",
                    "applied_hunks": 0,
                }

            # Count hunks in the patch
            hunk_count = patch_content.count("@@ ")

            return {
                "error": None,
                "applied_hunks": hunk_count,
                "summary": f"Dry run: Would apply {hunk_count} hunks to {filepath}",
            }
        except Exception as e:
            return {"error": str(e), "applied_hunks": 0}

    def patch_apply(self, filepath: str, patch_content: str) -> Dict[str, Any]:
        """Apply a patch to a file."""
        try:
            # Use the existing apply_patch function
            result = apply_patch(filepath, patch_content, self.path_jail)
            return result
        except Exception as e:
            return {"error": str(e), "applied_hunks": 0}


# Convenience functions for the agent tools system
def create_ticket_manager(root_path: str = "./") -> TicketManager:
    """Create a ticket manager instance."""
    return TicketManager(root_path)


def create_patch_manager(root_path: str = "./") -> PatchManager:
    """Create a patch manager instance."""
    return PatchManager(root_path)


# Export functions that can be used as agent tools
async def ticket_new(file: str, lines: str, note: str, root_path: str = "./") -> str:
    """Create a new coding ticket."""
    manager = TicketManager(root_path)
    return manager.ticket_new(file, lines, note)


async def ticket_next(root_path: str = "./") -> Optional[Dict[str, Any]]:
    """Get the next pending ticket."""
    manager = TicketManager(root_path)
    return manager.ticket_next()


async def ticket_list(root_path: str = "./") -> List[Dict[str, Any]]:
    """List all tickets."""
    manager = TicketManager(root_path)
    return manager.ticket_list()


async def patch_dry_run(
    filepath: str, patch_content: str, root_path: str = "./"
) -> Dict[str, Any]:
    """Dry run a patch to see what would be changed."""
    manager = PatchManager(root_path)
    return manager.patch_dry_run(filepath, patch_content)


async def patch_apply(
    filepath: str, patch_content: str, root_path: str = "./"
) -> Dict[str, Any]:
    """Apply a patch to a file."""
    manager = PatchManager(root_path)
    return manager.patch_apply(filepath, patch_content)


async def diff_file(filepath: str, root_path: str = "./") -> str:
    """Show unified diff of a file compared to its original state."""
    try:
        safe_path = Path(root_path) / filepath
        if not safe_path.exists():
            return f"[diff] File does not exist: {safe_path}"

        # For now, we'll just return a placeholder diff
        # In a real implementation, this would compare with a backup or git repo
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Return a simple representation of the file content as a diff
        lines = content.split("\n")
        diff_lines = []
        for _i, line in enumerate(lines, 1):
            diff_lines.append(f"+{line}")  # Mark all lines as additions for simplicity

        return "\n".join(diff_lines)
    except Exception as e:
        return f"[diff] Error generating diff: {str(e)}"
