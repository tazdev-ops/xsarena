#!/usr/bin/env bash
set -euo pipefail
APPLY="${APPLY:-0}"

mv2() { src="$1"; dst="$2"; [ -f "$src" ] || return 0; [ -e "$dst" ] && { echo "SKIP (exists): $dst"; return 0; }
  echo "mv '$src' → '$dst'"; if [ "$APPLY" = "1" ]; then mkdir -p "$(dirname "$dst")"; git mv "$src" "$dst" 2>/dev/null || mv "$src" "$dst"; fi; }
rm2() { f="$1"; [ -f "$f" ] || return 0; echo "rm '$f'"; [ "$APPLY" = "1" ] && (git rm -f "$f" 2>/dev/null || rm -f "$f"); }
append_unique() { line="$1"; file="$2"; touch "$file"; grep -qxF "$line" "$file" || echo "$line" >> "$file"; }

# 1) Rules: move root rules under sources/
mv2 "CLI_AGENT_RULES.md" "directives/_rules/sources/CLI_AGENT_RULES.md"

# 2) Roles: group all role.*.md into directives/roles/
mkdir -p "directives/roles"
for f in directives/role.*.md; do
  [ -f "$f" ] && mv2 "$f" "directives/roles/$(basename "$f")"
done
# Keep role_launcher.md in directives/ (it's a launcher spec). Optionally:
# mv2 "directives/role_launcher.md" "directives/roles/README.md"

# 3) QuickRefs: group all agent_quickref.* into quickref/
mkdir -p "directives/quickref"
for f in directives/agent_quickref*.md; do
  [ -f "$f" ] && mv2 "$f" "directives/quickref/$(basename "$f")"
done

# 4) Prompts: move root prompt_*.txt into directives/prompts/
mkdir -p "directives/prompts"
for f in prompt_*.txt; do
  [ -f "$f" ] && mv2 "$f" "directives/prompts/$(basename "$f")"
done

# 5) Snapshot artifacts: remove and ignore
rm2 "xsa_min_snapshot.txt"
rm2 "xsa_min_snapshot_final.txt"
rm2 "xsa_min_snapshot_post_fix.txt"
if [ -d "snapshot_chunks" ]; then
  echo "cleanup: snapshot_chunks/*"
  if [ "$APPLY" = "1" ]; then rm -f snapshot_chunks/* || true; fi
fi
append_unique "snapshot_chunks/" .gitignore
append_unique "xsa_min_snapshot*.txt" .gitignore

# 6) Optional: ignore review/ (or keep under version control if you want reproducible probes)
# append_unique "review/" .gitignore

echo "Dry-run complete. Re-run with: APPLY=1 bash scripts/declutter_phase2.sh"

# 7) Rebuild merged rules (only when APPLY=1 and script exists)
if [ "$APPLY" = "1" ] && [ -x "scripts/merge_session_rules.sh" ]; then
  bash scripts/merge_session_rules.sh || true
  echo "Rebuilt directives/_rules/rules.merged.md"
fi