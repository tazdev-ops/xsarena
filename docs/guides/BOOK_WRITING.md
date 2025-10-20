# Book Writing Guide

## Basic Workflow

### 1. Plan
```bash
# Let AI generate outline
xsarena run book "Roman History" --plan

# Or start directly
xsarena run book "Roman History"
```

### 2. Configure Style
```bash
# Length (chars per chunk)
--length standard    # 4200 chars
--length long        # 5800 chars
--length very-long   # 6200 chars

# Span (total chunks)
--span medium        # 12 chunks
--span long          # 24 chunks
--span book          # 40 chunks

# Style overlays
xsarena author style-narrative on
xsarena author style-nobs on
```

### 3. Run
```bash
xsarena run book "Roman History" \
  --length long \
  --span book \
  --out ./books/roman_history.final.md \
  --follow
```

### 4. Monitor
```bash
xsarena ops jobs follow <job_id>
xsarena ops jobs summary <job_id>
```

### 5. Guide Output (optional)
```bash
# Send hint for next chunk
xsarena ops jobs next <job_id> "Focus on Punic Wars"

# Pause and redirect
xsarena ops jobs pause <job_id>
xsarena ops jobs resume <job_id>
xsarena ops jobs next <job_id> "Transition to Empire"
```

## Advanced

### Continue Existing Book
```bash
xsarena run continue ./books/roman_history.final.md \
  --length long \
  --span medium
```

### Use Recipes
```bash
# Interactive textbook
export SUBJECT="Machine Learning"
xsarena run from-recipe recipes/interactive_textbook.yml

# Cookbook
export SUBJECT="Python Patterns"
xsarena run from-recipe recipes/cookbook.yml
```

### Quality Control

**During generation:**
```bash
xsarena settings set --repetition-warn
xsarena settings set --coverage-hammer
```

**After generation:**
```bash
xsarena analyze continuity ./books/roman_history.final.md
xsarena study generate flashcards ./books/roman_history.final.md
```

## Best Practices

**Do:**
- ✅ Use `--follow` to wait for completion
- ✅ Enable repetition warnings
- ✅ Review first few chunks
- ✅ Use descriptive output filenames

**Don't:**
- ❌ Run multiple jobs to same file
- ❌ Interrupt without pause
- ❌ Ignore repetition warnings

## Example Workflows

**Quick book (30-60 min):**
```bash
xsarena run book "Quick Topic" \
  --length standard \
  --span medium \
  --follow
```

**Comprehensive book (2-4 hours):**
```bash
xsarena run book "Deep Topic" \
  --length very-long \
  --span book \
  --profile clinical-masters \
  --follow
```
