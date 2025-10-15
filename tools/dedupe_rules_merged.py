#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path
B=re.compile(r"<!--\s*===== BEGIN:\s*(.+?)\s*=====.*-->")
E=re.compile(r"<!--\s*===== END:\s*(.+?)\s*=====.*-->")
def run(p: Path)->bool:
  s=p.read_text(encoding="utf-8",errors="replace").splitlines(True)
  out=[]; seen=set(); i=0; ch=False
  while i<len(s):
    m=B.match(s[i].strip())
    if m:
      key=m.group(1).strip(); block=[s[i]]; i+=1
      while i<len(s):
        block.append(s[i])
        if E.match(s[i].strip()): i+=1; break
        i+=1
      if key in seen: ch=True
      else: seen.add(key); out.extend(block)
      continue
    out.append(s[i]); i+=1
  if ch: p.write_text("".join(out), encoding="utf-8")
  return ch
if __name__=="__main__":
  p=Path(sys.argv[1] if len(sys.argv)>1 else "directives/_rules/rules.merged.md")
  if p.exists(): print("[OK]" if run(p) else "[NOTE] no dupes")
