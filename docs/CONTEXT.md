# Pinned short state of the world; max 15 lines

## What changed this week
- Agent journal system implemented for session continuity
- New documentation files added for handoffs and startup

## Current defaults (style, knobs)
- Default style: narrative with teach-before-use
- Output minchars: 3000
- Continuation: anchor mode
- Repetition guard: on with 0.35 threshold

## Known caveats (CF, timeouts)
- Bridge may require Cloudflare challenge solving
- Use 60s timeouts for normal operations
- 180s timeouts for heavy operations

## Next planned steps
- Implement notification system for long-running tasks
- Review and update documentation as needed
