#!/usr/bin/env python3
import argparse
import json
import os
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=".lint/ruff.json")
    ap.add_argument("--rules", default="E,F,I", help="comma list (e.g. E,F,I or E9,F)")
    ap.add_argument("--max-per-ticket", type=int, default=8)
    ap.add_argument("--outdir", default=".lint/tickets")
    args = ap.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules = {r.strip() for r in args.rules.split(",") if r.strip()}
    by_file = defaultdict(list)
    for item in data:
        code = item.get("code") or ""
        if rules and not any(code.startswith(r) for r in rules):
            continue
        by_file[item["filename"]].append(item)

    os.makedirs(args.outdir, exist_ok=True)
    index = []
    tid = 1
    for filename, issues in sorted(by_file.items(), key=lambda kv: len(kv[1]), reverse=True):
        # chunk issues for this file
        for i in range(0, len(issues), args.max_per_ticket):
            chunk = issues[i : i + args.max_per_ticket]
            ticket = {
                "id": f"ticket_{tid:04d}",
                "file": filename,
                "rules": sorted({x["code"] for x in chunk}),
                "issues": [
                    {
                        "code": x["code"],
                        "message": x["message"],
                        "line": x["location"]["row"],
                        "col": x["location"]["column"],
                    }
                    for x in chunk
                ],
                "done": False,
            }
            path = os.path.join(args.outdir, f"{ticket['id']}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(ticket, f, indent=2, ensure_ascii=False)
            index.append({"path": path, "id": ticket["id"], "file": filename, "count": len(chunk)})
            tid += 1

    # write queue index
    with open(os.path.join(args.outdir, "queue.json"), "w", encoding="utf-8") as f:
        json.dump({"tickets": index}, f, indent=2)
    print(f"[ruff_batch] {len(index)} tickets → {args.outdir}/queue.json")


if __name__ == "__main__":
    main()
