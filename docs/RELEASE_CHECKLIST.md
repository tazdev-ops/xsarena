# Release Checklist

## Pre-release verification:
- [ ] QUICK_DOCTOR: Run `xsarena doctor env` (and nothing else)
- [ ] README refresh: Run `MODE: UPDATE_MANUAL` to ensure documentation is current
- [ ] Snapshot: Run `xsarena snapshot run` to document current state
- [ ] Publish tests: Verify `xsarena publish run <job_id> --epub --pdf` works
- [ ] Deprecation warnings: Verify deprecation messages still appear for old commands
- [ ] Cut tag: Create appropriate version tag after verification

## Additional checks:
- [ ] All new CLI commands documented in README
- [ ] Help text accurate for all commands
- [ ] Tutorials and examples still work
- [ ] Bridge and OpenRouter backends functional
- [ ] Job management works properly
- [ ] Serve, publish, and audio commands operational
