#!/usr/bin/env bash
set -euo pipefail
fail(){ echo "[FAIL] $*"; exit 1; }; warn(){ echo "[WARN] $*"; }
echo "== prepush_check =="
command -v ruff >/dev/null 2>&1 && ruff check . || warn "ruff not installed"
command -v black >/dev/null 2>&1 && black --check . || warn "black not installed"
command -v mypy >/dev/null 2>&1 && mypy . || warn "mypy missing/fail"
command -v pytest >/dev/null 2>&1 && pytest -q || warn "pytest missing/fail"
[[ -f scripts/gen_docs.sh ]] && bash scripts/gen_docs.sh || true
git diff --exit-code || fail "Docs drift; commit docs"
TRACKED="$(git ls-files)"
for pat in '^snapshot_chunks/' '^xsa_.*snapshot.*\.txt$' '^review/.*\.tar\.gz$' '^\.xsarena/tmp/'; do
  hits=$(echo "$TRACKED" | grep -E "$pat" || true)
  [[ -z "$hits" ]] || { echo "$hits" | sed 's/^/ - /'; fail "Banned artifact(s): $pat"; }
done
ep=()
while IFS= read -r f; do head -n1 "$f" | grep -q "XSA-EPHEMERAL" && ep+=("$f") || true; done < <(git ls-files)
[[ ${#ep[ @]} -eq 0 ]] || { printf '%s\n' "${ep[ @]}" | sed 's/^/ - /'; fail "XSA-EPHEMERAL files are tracked"; }
echo "[OK ] prepush checks passed"
