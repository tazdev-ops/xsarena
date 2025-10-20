# Investigation: Incomplete V2/V3 migrations

## Findings
- Multiple warnings.warn("Using new JobsV3 system", DeprecationWarning, stacklevel=2) found in cmds_run.py
- NotImplementedError in src/xsarena/core/engine.py line 61 for autopilot_run method
- Multiple files reference JobsV3, JobV3, and v2_orchestrator
- Autopilot FSM exists but raises NotImplementedError

## Code locations
- src/xsarena/cli/cmds_run.py: Multiple JobsV3 deprecation warnings
- src/xsarena/core/engine.py: autopilot_run raises NotImplementedError
- src/xsarena/core/autopilot/fsm.py: FSM implementation exists but is not fully functional

## Conclusion
V2/V3 migration is in progress with deprecation warnings and incomplete features. The autopilot functionality is intentionally disabled with NotImplementedError.
