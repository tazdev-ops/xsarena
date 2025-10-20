# HIGHER AI RULER: no code. order. cli knows how to code. i mean no big codes perhaps just llike replace such with such

You are a command‑mode operator. Rules:
- Set NO_COLOR=1 and RICH_NO_COLOR=1
- Non‑interactive only; pass explicit flags (e.g., --resume/--overwrite; --wait false)
- Don’t pass large content via argv; write to files and pass paths

Do this (safe minimal snapshot bootstrap):
1) Show settings (sanity)
   xsarena settings show

2) Start bridge and poll health (optional for snapshot, healthy to keep running):
   xsarena ops service start-bridge-v2 >/dev/null 2>&1 &
   for i in {1..40}; do curl -s http://127.0.0.1:5102/v1/health | grep -q '"status":"ok"' && break; sleep 0.5; done

3) Preflight verify (fail on oversize/disallowed/secrets):
   xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed --fail-on secrets

4) If preflight OK, produce a lean flat pack:
   xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map

5) Postflight verify (structure + redaction markers):
   xsarena ops snapshot verify --file repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on disallowed --redaction-expected

6) Print result:
   ls -lh repo_flat.txt

If any step fails: paste stderr and propose the smallest policy change (add a --disallow glob or lower --max-per-file) and re‑run verify. Do not edit code.
