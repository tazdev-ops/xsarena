# XSArena Implementation Verification Checklist

## Purpose
This checklist allows the CLI agent to verify all implementations demanded up to the "think more" point. It includes health checks, commands, scripts, docs, and rules. The lower AI is unreliable and may have context issues, so this checklist helps ensure completeness.

## Section 1: Health and Core Functionality Checks

- [ ] **Health Check**: Commands `xsarena fix run`, `xsarena backend test`, `xsarena doctor run` exist and run without errors.
  - Verify: Run each; expect no fatal errors (warnings OK).
  - Note: `xsarena doctor run` may not exist, use `xsarena backend test` instead.

- [ ] **Adapt Inspect**: `xsarena adapt inspect` exists and outputs a JSON plan to `review/adapt_plan_*.json`.
  - Verify: Run it; check if `review/adapt_plan_*.json` is created.

- [ ] **Clean Sweep**: `xsarena clean sweep` exists and lists ephemeral files (dry-run mode).
  - Verify: Run `xsarena clean sweep`; expect output showing candidates.

- [ ] **Snapshot Write**: `xsarena snapshot write` exists and writes to `~/xsa_min_snapshot.txt`.
  - Verify: Run it; check if the file exists in your home directory with a manifest section.

- [ ] **Report Quick**: `xsarena report quick` exists and creates a tar.gz bundle in `review/report_*.tar.gz`.
  - Verify: Run `xsarena report quick`; check if the tar.gz is created.

- [ ] **Boot Read**: `xsarena boot read` exists and reads from startup.yml.
  - Verify: Run it; expect "=== Startup Read Summary ===" output.

- [ ] **Merge Rules**: `scripts/merge_session_rules.sh` exists and rebuilds `directives/_rules/rules.merged.md`.
  - Verify: Run `bash scripts/merge_session_rules.sh`; check if the merged file updates.

## Section 2: Core CLI Structure and Commands

- [ ] **CLI Entry**: `xsarena` runs without errors (Typer app in src/xsarena/cli/main.py).
  - Verify: `xsarena --help` shows commands.

- [ ] **Backend Configuration**: `xsarena backend show` and `xsarena backend test` work.
  - Verify: Run commands; expect configuration info and health check.

- [ ] **Session State**: `.xsarena/` directory exists and contains configuration files.
  - Verify: Check `.xsarena/config.yml` exists.

- [ ] **Book Commands**: `xsarena book --help` shows available commands.
  - Verify: Run command; expect book-related subcommands.

- [ ] **Continue Command**: `xsarena continue --help` shows available commands.
  - Verify: Run command; expect continue-related subcommands.

## Section 3: New Features and Commands Added

- [ ] **Adapt Suppress**: `xsarena adapt suppress-add`, `suppress-ls`, `suppress-clear` commands exist.
  - Verify: Run `xsarena adapt suppress-ls`; expect JSON output of suppressions.

- [ ] **Boot Commands**: `xsarena boot read` and `xsarena boot init` exist.
  - Verify: Run `xsarena boot --help`; expect these commands listed.

- [ ] **Report Commands**: `xsarena report quick`, `job`, `full` exist.
  - Verify: Run `xsarena report --help`; expect these commands listed.

## Section 4: Scripts and Tools

- [ ] **Merge Session Rules**: `scripts/merge_session_rules.sh` exists and runs.
  - Verify: Run script; expect "Merged → directives/_rules/rules.merged.md".

- [ ] **Prepush Check**: `scripts/prepush_check.sh` exists and runs.
  - Verify: Run script; expect various checks to pass.

- [ ] **Snapshot Tools**: `tools/minimal_snapshot_optimized.py` exists.
  - Verify: File exists in tools/ directory.

- [ ] **Chunking Tools**: `tools/snapshot_chunk.py` and `legacy/chunk_snapshot.sh` exist.
  - Verify: Both files exist and are executable.

## Section 5: Documentation Files

- [ ] **ROADMAP**: `ROADMAP.md` exists.
  - Verify: File exists and contains project goals.

- [ ] **SUPPORT**: `SUPPORT.md` exists.
  - Verify: File exists and explains how to get help.

- [ ] **CONFIG_REFERENCE**: `CONFIG_REFERENCE.md` exists.
  - Verify: File exists and lists configuration options.

- [ ] **MODULES**: `MODULES.md` exists.
  - Verify: File exists and describes module structure.

- [ ] **CHANGELOG**: `CHANGELOG.md` exists.
  - Verify: File exists and tracks changes.

- [ ] **STATE**: `docs/STATE.md` exists.
  - Verify: File exists and describes state management.

- [ ] **GIT_POLICY**: `docs/GIT_POLICY.md` exists.
  - Verify: File exists and describes git workflow.

## Section 6: Rules and Configuration

- [ ] **Canonical Rules**: `directives/_rules/rules.merged.md` exists.
  - Verify: File exists and contains merged rules.

- [ ] **Rules Sources**: `directives/_rules/sources/CLI_AGENT_RULES.md` exists.
  - Verify: File exists and contains source rules.

- [ ] **Orders Log**: `directives/_rules/sources/ORDERS_LOG.md` exists.
  - Verify: File exists and can be appended to.

- [ ] **Startup Config**: `.xsarena/ops/startup.yml` exists.
  - Verify: File exists and contains startup reading plan.

## Section 7: GitHub Templates

- [ ] **PR Template**: `.github/PULL_REQUEST_TEMPLATE.md` exists.
  - Verify: File exists in .github/PULL_REQUEST_TEMPLATE/ directory.

- [ ] **Issue Template**: `.github/ISSUE_TEMPLATE/bug_report.yml` exists.
  - Verify: File exists in .github/ISSUE_TEMPLATE/ directory.

## Section 8: Directory Structure and Git

- [ ] **Books Layout**: `books/finals` directory exists.
  - Verify: Directory exists and contains book files.

- [ ] **Recipes Directory**: `recipes/` directory exists.
  - Verify: Directory exists and contains recipe files.

- [ ] **Review Directory**: `review/` directory exists.
  - Verify: Directory exists (may be empty initially).

- [ ] **Git Ignore**: `.gitignore` includes ephemeral patterns.
  - Verify: Check file contains patterns like `review/`, `snapshot_chunks/`, etc.

## Section 9: Snapshot and Chunking Verification

- [ ] **Optimized Snapshot**: `tools/minimal_snapshot_optimized.py` creates 300-400KB snapshots.
  - Verify: Run script; check `~/xsa_min_snapshot.txt` is 300-400KB.

- [ ] **Chunking to Home**: `legacy/chunk_snapshot.sh` outputs to `~/snapshot_chunks/`.
  - Verify: Run script; check chunks created in home directory.

- [ ] **Chunk Message**: Chunks contain "Just say received. do nothing. i will send you the rest of the code".
  - Verify: Check end of any chunk file contains this exact message.

## Section 10: Low AI Reliability Considerations

- [ ] **Anti-Recursion Rule**: Added to CLI_AGENT_RULES.md to check for previous snapshots in output.
  - Verify: Check rules file contains anti-recursion check instructions.

- [ ] **Size Constraint Rule**: Added to CLI_AGENT_RULES.md to maintain 300-400KB range.
  - Verify: Check rules file contains size constraint instructions.

## How to Use This Checklist

1. Go through each item and run the verification commands
2. Mark items as [✅] if they pass, [❌] if they fail, or [?] if uncertain
3. For any [❌] items, implement the missing functionality
4. Re-run verification after implementing missing items

**Total Items: 38**
**Expected Status: All should be [✅] after full implementation**
