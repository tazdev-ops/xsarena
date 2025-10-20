# Troubleshooting Guide

## Jobs

### Job stuck in RUNNING
**Diagnose:**
```bash
xsarena ops jobs summary <job_id>
xsarena ops jobs tail <job_id>
```

**Fix:**
1. Cancel: `xsarena ops jobs cancel <job_id>`
2. Check bridge: `curl http://localhost:5102/health`
3. Restart bridge if needed
4. Resume job or restart

### Job fails with "transport_unavailable"
**Cause:** Bridge not connected

**Fix:**
1. Restart bridge: `xsarena ops service start-bridge-v2`
2. Check Firefox tab has `#bridge=5102` in URL
3. Click retry on any message
4. Run: `xsarena ops health fix-run`

### Repetitive output
**Cause:** Repetition threshold too high or model looping

**Fix:**
1. Lower threshold: `xsarena settings set --repetition-threshold 0.25`
2. Enable warning: `xsarena settings set --repetition-warn`
3. Send next hint: `xsarena ops jobs next <job_id> "Continue with X"`

## Bridge

### "Browser client not connected"
**Check:**
1. Firefox tab open with model page
2. URL has `#bridge=5102`
3. Userscript installed and enabled
4. Bridge server running: `curl http://localhost:5102/health`

## Output Quality

### Output too short
**Fix:**
1. Increase: `xsarena settings set --output-min-chars 6000`
2. More passes: `xsarena settings set --output-push-max-passes 5`
3. Use longer span: `--span book`

### Too many bullet points
**Fix:**
1. Enable narrative: `xsarena author style-narrative on`
2. Use profile: `--profile clinical-masters`

## Diagnostic Commands

```bash
# Health check
xsarena ops health quick
xsarena ops health fix-run

# Job info
xsarena ops jobs ls --json
xsarena ops jobs follow <id>

# Config check
xsarena settings show
```
