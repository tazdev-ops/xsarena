#!/usr/bin/env bash
set -euo pipefail
mkdir -p review .xsarena/jobs_backup
echo "[1/5] backing up jobs..."
cp -r .xsarena/jobs ".xsarena/jobs_backup/$(date +%Y%m%d-%H%M)" 2>/dev/null || true
echo "[2/5] saving diff + snapshot..."
git diff > review/last.diff || true
python tools/min_snapshot.py "review/xsa_min_snapshot_emergency.txt" || true
echo "[3/5] rolling back working copy..."
git restore --staged -A 2>/dev/null || true
git checkout -- . 2>/dev/null || true
git reset --hard HEAD 2>/dev/null || true
echo "[4/5] health..."
xsarena fix run || true
xsarena backend ping || true
xsarena doctor run || true
echo "[5/5] done. Attach review/xsa_min_snapshot_emergency.txt + review/last.diff if you escalate."