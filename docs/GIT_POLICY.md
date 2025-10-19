# XSArena Git/CI Policy (Lean)
- Branching: work on feat/<topic>, fix/<topic>, chore/<topic>, ops/<topic>; main is protected.
- Commits: Conventional commits (feat:, fix:, chore:, docs:, refactor:, test:, build:, ci:). Small, cohesive.
- Pre-push: run scripts/prepush_check.sh (lint/tests/help drift; no ephemeral in diff).
- PRs: title in conventional format; include What/Why/How tested; CI must pass; squash-merge preferred.
- Releases: bump __version__, tag vx.y.z, update CHANGELOG.
- Recovery: scripts/emergency_checklist.sh; xsarena report quick; xsarena snapshot write.
