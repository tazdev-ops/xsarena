#!/usr/bin/env bash
set -euo pipefail

echo "== XSArena smoke test =="
fail() { echo "!! $*" >&2; exit 1; }
info() { echo "-- $*"; }

# 1) CLI sanity
info "CLI basics"
xsarena version || fail "version failed"
xsarena --help >/dev/null || fail "help failed"
xsarena --backend bridge --model default --window 42 settings show >/dev/null || fail "settings show failed"

# 2) Bridge up (start in background)
info "Starting bridge..."
( xsarena ops service start-bridge-v2 ) >/dev/null 2>&1 &
BRIDGE_PID=$!
trap 'kill $BRIDGE_PID >/dev/null 2>&1 || true' EXIT

# wait for health
for i in {1..40}; do
  STATUS=$(curl -s http://127.0.0.1:5102/v1/health | tr -d '\n' || true)
  if echo "$STATUS" | grep -q '"status":"ok"'; then
    info "Bridge health OK"
    break
  fi
  sleep 0.5
done

# 3) Offline simulate
info "Simulate"
xsarena dev simulate "Sanity Subject" --length standard --span medium >/dev/null || fail "simulate failed"
xsarena ops jobs ls || fail "jobs ls failed"

# 4) Dry-run
info "Run dry"
xsarena run book "Sanity Subject" --dry-run >/dev/null || fail "run dry failed"

# 5) Continue
info "Continue"
mkdir -p books
echo "# Test" > ./books/Resume_Test.final.md
xsarena run continue ./books/Resume_Test.final.md --length standard --span medium --no-wait >/dev/null || fail "continue failed"

# 6) Docs
info "Docs gen-help"
xsarena docs gen-help >/dev/null || fail "docs gen-help failed"
test -f docs/_help_root.txt || fail "docs root help missing"

# 7) Optional snapshot verify
if xsarena ops snapshot verify --help >/dev/null 2>&1; then
  info "Snapshot verify (preflight)"
  xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow 'books/**' --disallow 'review/**' --disallow '.xsarena/**' --fail-on oversize --fail-on disallowed >/dev/null || fail "snapshot verify failed"
else
  info "Snapshot verify not available; skipping"
fi

echo "== OK =="
exit 0
