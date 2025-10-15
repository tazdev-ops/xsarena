# Troubleshooting

Bridge-first:
- Start: xsarena service start-bridge
- Browser: install/enable lmarena_bridge.user.js; open LMArena; click Retry once
- Ping: xsarena backend ping; xsarena doctor ping

OpenRouter fallback:
- export OPENROUTER_API_KEY=...
- xsarena backend ping --backend openrouter

Short chunks:
- Increase --min and --passes; set narrative on; compressed off

Repetition/restarts:
- cont.mode anchor; repetition warn on; anchors >= 200–300 chars

Doctor flow:
- xsarena doctor env; xsarena doctor ping; xsarena doctor run

Reports:
- xsarena report quick --book <path>
- xsarena report handoff --book <path>
