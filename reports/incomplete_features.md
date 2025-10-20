# Incomplete Features / Migrations

## JobsV3 Migration
- Status: Active migration, deprecation warnings present
- Files: src/xsarena/core/jobs/*.py
- Action: None required, intentional migration in progress

## Autopilot FSM
- Status: Implemented but raises NotImplementedError
- Files: src/xsarena/core/autopilot/fsm.py, src/xsarena/core/engine.py
- Action: Feature is intentionally disabled, users directed to standard runners

## Stubbed Mode Commands
- Files: src/xsarena/cli/cmds_modes.py
- Action: Commands exist but have no effect (intentionally stubbed)

## Recommendation
Accept these as work-in-progress; do not block on them.
