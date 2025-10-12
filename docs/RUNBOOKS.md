# Runbooks - Copy-paste Workflows

This document contains standardized workflows and procedures for common XSArena operations.

## Core Workflows

### Mastery Book Generation
For long, comprehensive book runs with maximum depth:

Settings to use:
- Style: compressed narrative (avoid lists/drills/vignettes)
- Output: minchars ≈ 4200-5200
- Chunks: 24+ for comprehensive coverage
- Continuation: anchor mode with coverage hammer

Commands:
```
xsarena z2h "Your Topic" --out=./books/topic.final.md --max=24 --min=4500
```

### Lossless-First Pipeline
For corpus → synthesis → lossless rewrite → book:

1. Import source materials: `xsarena import sources/corpus/`
2. Create synthesis: `xsarena lossless run sources/corpus/ --outdir=data/`
3. Rewrite losslessly: `xsarena rewrite.lossless data/corpus.synth.md`
4. Generate book: Use mastery settings from above

### Quick Study Material Generation
For rapid exam prep materials:
```
xsarena exam cram "Your Topic"
xsarena flashcards from books/topic.synth.md books/topic.flashcards.md
xsarena glossary from books/topic.synth.md books/topic.glossary.md
xsarena index from books/topic.synth.md books/topic.index.md
```

## Job Management Workflows

### Job Lifecycle
1. Submit: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
2. Run: `xsarena jobs run recipes/topic.yml`
3. Monitor: `xsarena jobs log <job_id>`
4. Resume: `xsarena jobs resume <job_id>`
5. Fork: `xsarena jobs fork <job_id> --backend openrouter`
6. Summary: `xsarena jobs summary <job_id>`

### Troubleshooting Jobs
When jobs stall or fail:
1. Check status: `xsarena jobs ls`
2. Examine logs: `xsarena jobs log <job_id>`
3. Cancel if needed: `xsarena jobs cancel <job_id>`
4. Resume: `xsarena jobs resume <job_id>`
5. Fork to different backend if needed: `xsarena jobs fork <job_id> --backend openrouter`

## Quality Assurance Workflows

### Content Quality Check
```
xsarena quality score books/topic.md
xsarena quality uniq books/topic.md
xsarena quality gate --min-score=7.5 books/topic.md
```

### Style Application
```
xsarena style.capture books/reference_style.md style_profiles/reference.style.md
xsarena style.apply style_profiles/reference.style.md "New Topic" books/new_topic_styled.md
```

## Multi-Agent Pipeline
For enhanced content using specialized agents:
```
# Uses outliner → writer → editor → continuity agents
xsarena z2h "Topic" --playbook z2h_multi --max=12 --min=3500
```

## Snapshot & Backup Workflows

### Project Snapshots
```
xsarena snapshot run
# For large projects: xsarena snapshot run --chunk
```

### Configuration Backup
Always backup project configuration before major changes:
```
cp .xsarena/project.yml backup/project_config_$(date +%Y%m%d).yml
```

## Health Checks

### Environment Check
```
xsarena doctor env
```

### Smoke Test
```
xsarena doctor run --subject "Smoke" --max 2 --min 800
```

## Advanced Workflows

### Bilingual Content Generation
```
xsarena bilingual.file books/english_content.md --lang=español --outdir=books/
```

### Policy Document Generation
```
xsarena policy.from regulations/law_document.txt outputs/ --org="Organization" --jurisdiction="Location"
```

## Performance Optimization

### Backend Selection
- Bridge: Browser-based, good for interactive sessions
- OpenRouter: Direct API, better for long runs
- Fallback: Automatic failover when primary unavailable

### Resource Management
- Monitor job resource usage: `xsarena jobs summary <job_id>`
- Clean up completed jobs: `xsarena jobs cancel <job_id>` (if no longer needed)
- Use appropriate chunk sizes for content type
