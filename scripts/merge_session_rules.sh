#!/usr/bin/env bash
set -euo pipefail
out="directives/_rules/rules.merged.md"
mkdir -p "directives/_rules"
: > "$out"

add() { f="$1"; [ -f "$f" ] || return 0
  echo -e "\n\n<!-- ===== BEGIN: $f ===== -->\n" >> "$out"
  sed 's/\t/    /g' "$f" >> "$out"
  echo -e "\n<!-- ===== END: $f ===== -->\n" >> "$out"
}

# Prefer new sources path; fall back to repo root for legacy
add "directives/_rules/sources/CLI_AGENT_RULES.md"
add "directives/_rules/sources/ORDERS_LOG.md"
add "CLI_AGENT_RULES.md"

# Add rules from sources directory
find directives/_rules/sources -maxdepth 1 -type f -name "*.md" | sort -f | while read -r f; do add "$f"; done

# Add other directive files from main directives directory
find directives -maxdepth 1 -type f -name "role.*.md" | sort -f | while read -r f; do add "$f"; done
find directives -maxdepth 1 -type f -name "style.*.md" | sort -f | while read -r f; do add "$f"; done

echo "Merged → $out"
python tools/dedupe_rules_merged.py directives/_rules/rules.merged.md || true
