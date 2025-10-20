# Snapshot QA Checklist (agent/human)

Before
- Decide type:
  - Minimal → txt (ultra-tight)
  - Maximal → write (tight/full) + zip
- Load policy (optional): .xsarena/ops/snapshot_policy.yml
- Preflight verify (for minimal): fail if oversize/disallowed/secrets

Make it
- Minimal (txt): ultra-tight preset; caps set; --no-repo-map
- Maximal (write): tight/full mode; zip format; turn off context unless required

Verify
- Preflight: OK or actionable violations
- Postflight (flat pack): structural boundaries parse; no oversize/disallowed; redaction markers present (if expected)

Fix (if needed)
- Adjust budgets/include/exclude via policy or flags
- Run secret scan; remove secrets; keep redaction on for txt
- Only propose code fixes if the builder crashes (see FIX_PLAYBOOK)

Good to share when
- repo_flat.txt ≤ total_max; no violations; redacted
- Or xsa_snapshot.zip built successfully and plan documented (what mode/context used)

This pack keeps your snapshots predictable, safe, and agent‑friendly:
- Rules and policies the agent can follow
- Clear commands for minimal and maximal outputs
- A verify gate to enforce budgets and safety
- A fix playbook if (and only if) something breaks under the hood
