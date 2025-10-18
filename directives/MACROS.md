# Workshop & Writing Clinic Kit Macros

## Workshop Kit Macros

### Agenda macro
```bash
xsarena macros add wshop 'xsarena prompt run -s directives/prompt.workshop_agenda.json.md -t "$1" > review/workshop.$(date +%s).json'
```

### Decision macro
```bash
xsarena macros add dlog 'xsarena prompt run -s directives/prompt.decision_record.json.md -t "$1" > review/decision.$(date +%s).json'
```

## Writing Clinic Kit Macros

### Outline diagnosis macro
```bash
xsarena macros add odoc 'xsarena prompt run -s directives/prompt.outline_diagnosis.json.md -t "$1" > review/outline_diag.$(date +%s).json'
```

### Style check macro
```bash
xsarena macros add scheck 'xsarena prompt run -s directives/prompt.style_check.json.md -t "$1" > review/style.$(date +%s).json'
```

### Glossary macro
```bash
xsarena macros add gloss 'xsarena prompt run -s directives/prompt.glossary_make.json.md -t "$1" > review/glossary.$(date +%s).json'
```
