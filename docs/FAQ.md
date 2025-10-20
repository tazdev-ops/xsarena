# Frequently Asked Questions

## General

**What is XSArena?**
Tool for AI-assisted long-form content creation (books, manuals, guides).

**Do I need an API key?**
- Bridge mode: No (uses browser)
- OpenRouter: Yes (`OPENROUTER_API_KEY`)

**Which mode should I use?**
- Bridge: Free, requires Firefox + userscript
- OpenRouter: Paid, API-based, more reliable

## Book Generation

**How long does generation take?**
- Short (12 chunks, standard): 30-60 min
- Medium (24 chunks, long): 1-2 hours
- Long (40 chunks, very-long): 3-5 hours

**Can I stop and resume?**
Yes!
```bash
xsarena ops jobs pause <job_id>
xsarena ops jobs resume <job_id>
xsarena ops jobs cancel <job_id>
```

**Output too short?**
1. `--output-min-chars 6000`
2. `--output-push-max-passes 5`
3. `--span book` (40 chunks)

**Too many bullet points?**
```bash
xsarena author style-narrative on
```

**Repetitive content?**
```bash
xsarena settings set --repetition-threshold 0.25
xsarena settings set --repetition-warn
```

## Technical

**Bridge won't connect?**
1. `curl http://localhost:5102/health`
2. Firefox tab open with `#bridge=5102` in URL
3. Userscript active
4. Click retry on message

**Jobs stuck?**
```bash
xsarena ops jobs summary <job_id>
xsarena ops jobs tail <job_id>
xsarena ops health fix-run
```

**Where are jobs stored?**
```
.xsarena/jobs/<job_id>/
  ├── job.json
  ├── events.jsonl
  └── run_manifest.json
```

## Best Practices

**Recommended settings?**
```bash
xsarena settings set --output-min-chars 4500
xsarena settings set --output-push-max-passes 2
xsarena settings set --repetition-warn
xsarena author style-narrative on
xsarena author style-nobs on
```

**Ensure good quality?**
1. Use narrative + no_bs overlays
2. Enable repetition warnings
3. Monitor first few chunks
4. Analyze continuity after: `xsarena analyze continuity book.md`
