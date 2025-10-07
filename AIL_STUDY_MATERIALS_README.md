# Ancient Iranian Languages Study Materials for xsarena

This directory contains all the necessary files to create English study books, exam-cram materials, and study aids for Ancient Iranian Languages using xsarena CLI.

## Files and Directories

### Directories
- `sources/` - Contains topic-specific source files (persian_history_scripts, pre_islamic_history, linguistics)
- `data/` - Contains configuration files and blueprints
- `directives/` - Contains English directives and instructions
- `books/` - Output directory for generated books and study materials
- `review/` - Working directory for review materials

### Key Files
- `data/blueprint_ancient_iranian_languages.json` - Topic blueprint with percentages and focus areas
- `directives/ancient_iranian_languages.en.txt` - English-only directives for exam preparation
- `data/resource_map.ail.en.json` - Recommended resources mapped to topics
- `data/tag_map.ail.yml` - Topic slugs for folder naming
- `sources/*_corpus.md` - Concatenated corpora for each topic area
- `recipes/ail.en.yml` - Configuration recipe for book generation
- `books/ail.scripts.flashcards.md` - Heterogram flashcard deck
- `directives/narrative_overlay.ail.md` - Teach-before-use pedagogical overlay

## Usage Instructions

### Setup
1. Start xsarena CLI:
   ```
   xsarena   # or: python lma_cli.py
   ```

2. Connect backend:
   ```
   /capture  # then click Retry in browser
   ```

3. Load English directives:
   ```
   /systemfile directives/ancient_iranian_languages.en.txt
   ```

4. Enforce English + pedagogy:
   ```
   /system.append
   Output must be 100% English. If inputs contain Persian, translate first.
   Pedagogy: teach‑before‑use; section flow; short vignettes; quick checks; pitfalls.
   EOF
   ```

### Generate Books
You can generate either one comprehensive book or separate books for each topic:

For a single comprehensive book:
```
/repo.use book.zero2hero "Ancient Iranian Languages"
/book.zero2hero "Ancient Iranian Languages" --plan
```

For separate books by topic (recommended):
```
/repo.use book.zero2hero "Persian Language History & Scripts/Texts"
/book.zero2hero "Persian Language History & Scripts/Texts" --plan

/repo.use book.zero2hero "Pre‑Islamic Iranian History"
/book.zero2hero "Pre‑Islamic Iranian History" --plan

/repo.use book.zero2hero "Linguistics (General & Historical/Comparative)"
/book.zero2hero "Linguistics (General & Historical/Comparative)" --plan
```

### Generate Study Aids
```
/exam.cram "Ancient Iranian Languages"

# If you have created synths:
/flashcards.from books/ail.scripts.synth.md books/ail.scripts.flashcards.md 200
/glossary.from    books/ail.scripts.synth.md books/ail.scripts.glossary.md
/index.from       books/ail.scripts.synth.md books/ail.scripts.index.md
```

### Create Synth Files (Optional, Recommended once you have sources)
```
/ingest.synth sources/persian_history_scripts_corpus.md books/ail.scripts.synth.md 100 16000
/ingest.synth sources/pre_islamic_history_corpus.md books/ail.history.synth.md 100 16000
/ingest.synth sources/linguistics_corpus.md books/ail.linguistics.synth.md 100 16000
```

### Address Weak Areas
After any mock exam:
```
/book.pause
/next "Write a short repair chapter focusing on the highest‑frequency error patterns (heterograms, chronology, sound changes). Add 5 quick checks."
# paste your misses if available
/book.resume
```

## Optional Macro
The following macro can be used as a one-liner for topic processing:
```
/macro.save ail_run "/ingest.synth sources/${1|slug}_corpus.md books/${1|slug}.synth.md 100 16000 && /book.zero2hero ${2} --plan && /exam.cram ${2}"
```

Then use it as:
```
/macro.run ail_run persian_history_scripts "Persian Language History & Scripts/Texts"
```

## Notes
- The 30-item heterogram flashcard deck is included in books/ail.scripts.flashcards.md
- All output will be in English as specified in the directives
- The system will follow teach-before-use pedagogy with bolded definitions at first mention
