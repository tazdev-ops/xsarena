# Update Manual (MODE: UPDATE_MANUAL)

## 1) Gather help text (write to files, not chat):
- `timeout 60s xsarena --help | tee docs/_help_root.txt`
- Parse subcommands; for each:
  `timeout 60s xsarena <sub> --help | tee docs/_help_<sub>.txt`
- `grep -RIn ' @app\.command' src/xsarena/cli | tee docs/_cli_commands_grep.txt`

## 2) Refresh README sections: quick start, workflows, jobs, serve/publish/audio, styles/knobs, snapshot, troubleshooting, cheat sheet.

## 3) QUICK_DOCTOR (env) only; snapshot; report.

## 4) Anti-loop: if collection fails twice, stop and ask.# Migration Guide: LMA to XSA

## Command Mappings

### Core Commands
- `lma_cli.py` → `xsarena` (main entry point)
- `/book.zero2hero` → `xsarena z2h "topic"` (enhanced version)
- `/book.reference` → `xsarena book reference "topic"`
- `/book.nobs` → `xsarena book nobs "topic"`
- `/book.pop` → `xsarena book pop "topic"`

### Job Management
- `/jobs.ls` → `xsarena jobs ls`
- `/jobs.log` → `xsarena jobs log <id>`
- `/jobs.resume` → `xsarena jobs resume <id>`
- `/jobs.cancel` → `xsarena jobs cancel <id>`
- `/jobs.fork` → `xsarena jobs fork <id>`

### Quality & Style
- `/style.narrative` → `xsarena style narrative on/off`
- `/style.nobs` → `xsarena style nobs on/off`
- `/style.compressed` → `xsarena style compressed on/off`
- `/out.minchars` → `xsarena book minchars <N>`
- `/out.passes` → `xsarena book passes <N>`
- `/out.budget` → `xsarena book budget on/off`

### Synthesis & Rewrite
- `/ingest.synth` → `xsarena lossless ingest`
- `/rewrite.lossless` → `xsarena lossless rewrite`
- `/rewrite.start` → `xsarena lossless rewrite`

### Study Tools
- `/exam.cram` → `xsarena exam cram "topic"`
- `/flashcards.from` → `xsarena flashcards from`
- `/glossary.from` → `xsarena glossary from`
- `/index.from` → `xsarena index from`

### Backend & Service
- `/backend bridge/openrouter` → `xsarena --backend bridge/openrouter`
- `/or.model` → `xsarena --model <model>`
- `/service.start-bridge` → `xsarena service start-bridge`

### Health & Diagnostics
- `/doctor.env` → `xsarena doctor env`
- `/doctor.run` → `xsarena doctor run`
- `/serve.run` → `xsarena serve run`
- `/publish.run` → `xsarena publish run`
- `/audio.run` → `xsarena audio run`

## Directory Changes
- `lma_*` files → `xsarena` (main CLI)
- `.lmastudio/` → `.xsarena/` (local state directory)
- Legacy files remain for compatibility but show deprecation warnings

## Key Improvements in XSA
- Enhanced job management with better failover
- Improved continuation with anchor mode
- Better output control with budget and density knobs
- Unified command structure with Typer
- Improved documentation and help
