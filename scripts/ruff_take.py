#!/usr/bin/env python3
import json
import os
import sys

TICKETS_DIR = ".lint/tickets"
NEXT_PATH = ".lint/next.json"


def main():
    qpath = os.path.join(TICKETS_DIR, "queue.json")
    if not os.path.exists(qpath):
        print("[ruff_take] queue.json not found. Run ruff_snapshot + ruff_batch.", file=sys.stderr)
        sys.exit(1)
    with open(qpath, "r", encoding="utf-8") as f:
        q = json.load(f)

    # Find first not-done ticket by scanning ticket files
    for t in q.get("tickets", []):
        p = t["path"]
        try:
            with open(p, "r", encoding="utf-8") as f:
                ticket = json.load(f)
            if ticket.get("done"):
                continue
            # write NEXT pointer
            with open(NEXT_PATH, "w", encoding="utf-8") as out:
                json.dump(ticket, out, indent=2)
            # small console summary
            print(
                f"[NEXT] {ticket['id']} file={ticket['file']} "
                f"issues={len(ticket['issues'])} rules={','.join(ticket['rules'])}"
            )
            return
        except Exception:
            continue

    print("[ruff_take] No pending tickets.")
    sys.exit(2)


if __name__ == "__main__":
    main()
