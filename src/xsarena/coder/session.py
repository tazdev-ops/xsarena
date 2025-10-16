class CoderSession:
    def __init__(self, root: str):
        self.root = root
        self.tickets = []

    def ticket_new(self, file: str, lines, note: str):
        """Create a new ticket."""
        import uuid

        ticket_id = str(uuid.uuid4())[:8]  # Short UUID
        ticket = {"id": ticket_id, "file": file, "lines": lines, "note": note}
        self.tickets.append(ticket)
        return ticket_id

    def ticket_next(self):
        """Get the next pending ticket."""
        if self.tickets:
            return self.tickets[0]  # Return first ticket
        return None

    def patch_dry_run(self, ticket_id: str, patch_content: str):
        """Dry run a patch."""
        # Placeholder implementation
        return {"error": None, "applied_hunks": 1}

    def patch_apply(self, ticket_id: str, patch_content: str):
        """Apply a patch."""
        # Placeholder implementation
        return {"error": None, "applied_hunks": 1}

    def run_tests(self, args: str):
        """Run tests with pytest."""
        # Placeholder implementation
        return {"summary": f"[test] Running tests with args: {args}"}

    def diff_file(self, file: str):
        """Show file diff."""
        # Placeholder implementation
        return f"[diff] Diff for file: {file}"
