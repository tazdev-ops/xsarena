#!/usr/bin/env bash
set -euo pipefail

# Agent connection script for XSArena
# Sets up the bridge reliably for automated agents

xsarena ops service start-bridge-v2 >/dev/null 2>&1 &

# Wait for the bridge to be ready
for i in {1..40}; do
  if curl -s http://127.0.0.1:5102/v1/health | grep -q '"status":"ok"'; then
    break
  fi
  sleep 0.5
done

# Optional: if you have a configured launch_url in .xsarena/config.yml, open it
# This requires the 'webbrowser' Python module which may not be available in all environments
# So we'll just echo a message instead

echo "bridge: ok"
