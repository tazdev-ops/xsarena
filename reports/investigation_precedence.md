# Investigation: Config precedence order

## Expected precedence (highest priority last)
1. Hardcoded defaults
2. .xsarena/config.yml (project defaults)
3. .xsarena/session_state.json (user's last interactive settings) ← should override config
4. CLI flags (explicit overrides) ← highest priority

## Actual behavior
model: default
output_min_chars: 4500
Expected: model=from-session, output_min_chars=4500

## Code review
Check src/xsarena/cli/context.py CLIContext.load() method for the order of loading.

The docstring says:
1. Start with hardcoded SessionState() defaults
2. Load .xsarena/config.yml (project-level defaults) - SINGLE SOURCE OF TRUTH
3. Load .xsarena/session_state.json (user's last-used interactive settings) - PERSISTENCE ONLY, NO OVERRIDES
4. Apply CLI flags from cfg object (explicit, one-time overrides)

But the code implementation is wrong! It loads session_state.json first, then config.yml which overrides it.
However, there's a selective loading mechanism where only certain fields from session_state.json are loaded (like output_min_chars but not model).

## Conclusion
The precedence is indeed reversed from what would be expected. The config.yml is overriding session_state.json for some fields, and the selective field loading is causing inconsistent behavior.
