# XSArena Example Commands

This file contains ready-to-use command examples for different workflows.

## Book Authoring

### Nietzsche Study
```bash
# Create a detailed outline
xsarena run book outline "The philosophy of Friedrich Nietzsche"

# Write a no-bullshit manual about Nietzsche
xsarena run book nobs "Friedrich Nietzsche's philosophical works"

# Polish a draft chapter
xsarena run book polish "Your Nietzsche chapter text here..."
```

### Marx Study
```bash
# Create a comprehensive reference book
xsarena run book reference "Karl Marx's economic theories"

# Generate a zero-to-hero book on Marxism
xsarena run book zero2hero "Marxism and its impact on modern economics"

# Create a popular science book about Marx
xsarena run book pop "Karl Marx for beginners"
```

## Lossless Processing

### Text Improvement
```bash
# Rewrite text while preserving meaning
xsarena lossless rewrite "Your text to improve..."

# Run comprehensive lossless processing
xsarena lossless run "Your text to process..."

# Improve flow of a document
xsarena lossless improve-flow "Your document text..."
```

## Bilingual Processing

### Translation and Alignment
```bash
# Transform text between languages
xsarena bilingual transform --source-lang "English" --target-lang "Spanish" "Your text here..."

# Check translation alignment
xsarena mode alignment-check --source-text "Original" --translated-text "Translation" --source-lang "English" --target-lang "French"
```

## Policy Analysis

### Document Generation and Analysis
```bash
# Generate a policy document
xsarena policy generate-from-topic "Climate change mitigation" --requirements "Include economic impact and implementation timeline"

# Analyze policy compliance
xsarena policy analyze-compliance --policy "Your policy text" --evidence-files "evidence1.txt,evidence2.txt"
```

## Study Tools

### Flashcards and Quizzes
```bash
# Generate flashcards from content
xsarena study flashcards --content "Your study material..." --num-cards 15

# Create a quiz
xsarena study quiz --content "Your content..." --num-questions 10 --question-type "mixed"

# Create a glossary
xsarena study glossary --content "Your content..."
```

## Chad Mode (Evidence-Based Q&A)

### Direct Questions
```bash
# Answer a specific question
xsarena chad answer-question --question "What are the main tenets of behavioral economics?"

# Fact-check a statement
xsarena chad fact-check --statement "Climate change is primarily caused by human activities"
```

## Coding

### Code Generation
```bash
# Generate a complete project
xsarena coder code-project --requirements "Create a Python web scraper for news articles" --language "python"

# Fix code issues
xsarena coder fix-code --code "Your buggy code..." --issue "Function not returning expected values"

# Review code
xsarena coder review-code --code "Your code to review..." --language "javascript"
```

## Backend Configuration

### Switching Backends
```bash
# Set to bridge backend (default)
xsarena backend set bridge

# Set to OpenRouter with specific model
xsarena backend set openrouter --api-key "your-api-key" --model "openai/gpt-4o"

# Test current backend
xsarena backend test
```

## Mode Toggles

### Conversation Modes
```bash
# Set to battle mode
xsarena mode mode battle

# Set battle target to A
xsarena mode battle-target A

# Enable tavern mode (merge system messages)
xsarena mode tavern true

# Enable bypass mode
xsarena mode bypass true
```

## Debugging and State Management

### Session Management
```bash
# Show current session state
xsarena debug state

# Show current configuration
xsarena debug config

# Save current session
xsarena debug save-state ./session_backup.json

# Load a saved session
xsarena debug load-state ./session_backup.json
```

## Job Control

### Live Steering (Pause/Resume/Next/Cancel)
```bash
# Pause a running job
xsarena control pause <job_id>

# Resume a paused job
xsarena control resume <job_id>

# Send a hint to the next chunk of a job
xsarena control next <job_id> "hint text"

# Cancel a running job
xsarena control cancel <job_id>

# List all jobs
xsarena jobs list

# Show job status
xsarena jobs show <job_id>
```
