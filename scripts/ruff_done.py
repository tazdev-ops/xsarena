#!/usr/bin/env python3
import json
import os
import sys


def mark(path):
    with open(path, "r+", encoding="utf-8") as f:
        t = json.load(f)
    t["done"] = True
    with open(path, "w", encoding="utf-8") as f:
        json.dump(t, f, indent=2)
    print(f"[ruff_done] marked {os.path.basename(path)} done.")


def main():
    tickets_dir = ".lint/tickets"
    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        mark(sys.argv[1])
        return
    if len(sys.argv) == 2:
        # treat as id (ticket_0001)
        p = os.path.join(tickets_dir, f"{sys.argv[1]}.json")
        if os.path.exists(p):
            mark(p)
            return
    nextp = ".lint/next.json"
    if os.path.exists(nextp):
        # mark the actual ticket file as done
        with open(nextp, "r", encoding="utf-8") as f:
            nxt = json.load(f)
        p = os.path.join(tickets_dir, f"{nxt['id']}.json")
        if os.path.exists(p):
            mark(p)
            return
    print("[ruff_done] no ticket found to mark.")


if __name__ == "__main__":
    main()
