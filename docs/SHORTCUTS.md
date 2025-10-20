# Handy Shortcuts (Macros)

Save keystrokes by adding macros with the built-in utility.

Bridge
- xsarena utils macros add bridge-up 'xsarena ops service start-bridge-v2'
- xsarena utils macros add connect 'xsarena ops service connect'

Authoring lanes
- xsarena utils macros add run-dry 'xsarena run book "{SUBJECT}" --dry-run'
- xsarena utils macros add simulate 'xsarena dev simulate "{SUBJECT}" --length standard --span medium'

Snapshots
- xsarena utils macros add snap-txt 'xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map'

Analysis
- xsarena utils macros add qa 'xsarena analyze continuity ./books/*.final.md && xsarena analyze coverage --outline outline.md --book ./books/*.final.md'


Notes
- Replace {SUBJECT} as needed when you invoke macros; some shells require quoting.
- Macros are stored in .xsarena/macros.json; delete entries there to remove macros.

Append to your orders (CLI will merge/improve)
- If you've implemented ops service connect, mention it in USAGE and OPERATIONS.
- If you added ops snapshot verify, cross-link it from USAGE and TROUBLESHOOTING.
- If you implemented the directive root helper and Python-only rules merge, note them briefly in ARCHITECTURE.

This gives you a practical "done/not done" checklist, plus runnable scripts for Unix and Windows, and a JSON plan that your agent can consume. It stays lean while catching the biggest failure modes fast.
