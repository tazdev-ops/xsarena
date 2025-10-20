# XSArena Troubleshooting Guide

## Common Issues

### Bridge Connection Issues

**Problem**: "Bridge not reachable" error
**Solution**:
1. Start bridge: `xsarena ops service start-bridge-v2`
2. Check bridge health: `curl http://localhost:5102/health`
3. Verify userscript is connected (check bridge logs for "Userscript connected")

**Problem**: "Userscript client not connected"
**Solution**:
1. Install userscript in Tampermonkey/Greasemonkey
2. Open LMArena in browser with `#bridge=5102` in URL
3. Click "Retry" on any message to activate

### Job Issues

**Problem**: Job stuck in RUNNING state
**Solution**:
1. Check job status: `xsarena ops jobs summary <job_id>`
2. View logs: `xsarena ops jobs log <job_id>`
3. Cancel if needed: `xsarena ops jobs cancel <job_id>`

**Problem**: "Resumable job exists" error
**Solution**:
Use explicit flags: `--resume` to continue or `--overwrite` to start fresh

### Configuration Issues

**Problem**: Config file not loading
**Solution**:
1. Check file exists: `ls -la .xsarena/config.yml`
2. Validate YAML: `python -c "import yaml; yaml.safe_load(open('.xsarena/config.yml'))"`
3. Run health check: `xsarena ops health fix-run`

### Import Errors

**Problem**: "No module named 'xsarena.utils.prompt_cache'"
**Solution**:
This was a known bug that has been fixed. The caching feature was removed and the import issue resolved.

## Error Code Reference

- `transport_unavailable`: Network/bridge issues - check bridge is running
- `transport_timeout`: Request timeout - backend may be slow
- `auth_error`: Authentication failed - check API key
- `quota_exceeded`: Rate limit hit - wait or upgrade plan
- `api_error`: Backend returned error - check logs for details

## Getting Help

1. Create snapshot: `xsarena ops snapshot create --mode author-core`
2. Check recent jobs: `xsarena ops jobs ls`
3. Generate report: `xsarena report quick --book <path>`
4. Share snapshot and report when asking for help