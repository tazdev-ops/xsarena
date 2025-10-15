#!/usr/bin/env bash
# XSA-EPHEMERAL ttl=7d
# Usage:
#   scripts/quick_book.sh "Political History of the UK — Elections and Parties (c. 1832–present)"
set -euo pipefail

SUBJECT="${1:-}"
if [ -z "$SUBJECT" ]; then
  echo "Usage: $0 \"Subject Title\""
  exit 2
fi

PORT="${PORT:-8080}"
BACKEND="${BACKEND:-bridge}"
MAX="${MAX:-30}"       # total chunks — raise if you want more total length
MIN="${MIN:-5800}"     # per-chunk minimal chars (pushes long messages)
PASSES="${PASSES:-3}"  # micro-extends to hit MIN
OUT="./books/finals/$(echo "$SUBJECT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]\+/-/g;s/^-//;s/-$//').final.md"

echo "== XSArena Quick Book =="
echo "Subject: $SUBJECT"
echo "Backend: $BACKEND   Port: $PORT"
echo "Out:     $OUT"
echo

# 1) Ensure bridge is running (best-effort)
if ! curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "[bridge] starting on $PORT ..."
  xsarena service start-bridge --port "$PORT" --host 127.0.0.1 >/dev/null 2>&1 &
  # wait for health
  for i in $(seq 1 30); do
    sleep 1
    if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
      echo "[bridge] healthy."
      break
    fi
    if [ "$i" -eq 30 ]; then
      echo "[bridge] could not confirm health; continuing anyway."
    fi
  done
fi

# 2) Self-heal and ping
xsarena fix run || true
xsarena backend ping || true

# 3) Prompt for browser capture
cat <<EOF

Open https://lmarena.ai in your browser and add "#bridge=$PORT" to the URL.
In the chat UI, click "Retry" on any message to activate the tab.
Once done, press ENTER here to start generation.

EOF
read -r _

# 4) Run a long, dense narrative (no compressed) at max per-message
XSA_BACKEND="$BACKEND" xsarena fast start "$SUBJECT" \
  --base zero2hero \
  --no-bs \
  --narrative \
  --no-compressed \
  --max "$MAX" \
  --min "$MIN" \
  --passes "$PASSES" \
  --out "$OUT"

echo
echo "[done] Output → $OUT"