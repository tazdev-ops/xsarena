# LMASudio Example Commands

This file contains ready-to-use command examples for different workflows.

## Book Authoring

### Nietzsche Study
```bash
# Create a detailed outline
lmastudio book outline "The philosophy of Friedrich Nietzsche"

# Write a no-bullshit manual about Nietzsche
lmastudio book nobs "Friedrich Nietzsche's philosophical works"

# Polish a draft chapter
lmastudio book polish "Your Nietzsche chapter text here..."
```

### Marx Study
```bash
# Create a comprehensive reference book
lmastudio book reference "Karl Marx's economic theories"

# Generate a zero-to-hero book on Marxism
lmastudio book zero2hero "Marxism and its impact on modern economics"

# Create a popular science book about Marx
lmastudio book pop "Karl Marx for beginners"
```

## Lossless Processing

### Text Improvement
```bash
# Rewrite text while preserving meaning
lmastudio lossless rewrite "Your text to improve..."

# Run comprehensive lossless processing
lmastudio lossless run "Your text to process..."

# Improve flow of a document
lmastudio lossless improve-flow "Your document text..."
```

## Bilingual Processing

### Translation and Alignment
```bash
# Transform text between languages
lmastudio bilingual transform --source-lang "English" --target-lang "Spanish" "Your text here..."

# Check translation alignment
lmastudio mode alignment-check --source-text "Original" --translated-text "Translation" --source-lang "English" --target-lang "French"
```

## Policy Analysis

### Document Generation and Analysis
```bash
# Generate a policy document
lmastudio policy generate-from-topic "Climate change mitigation" --requirements "Include economic impact and implementation timeline"

# Analyze policy compliance
lmastudio policy analyze-compliance --policy "Your policy text" --evidence-files "evidence1.txt,evidence2.txt"
```

## Study Tools

### Flashcards and Quizzes
```bash
# Generate flashcards from content
lmastudio study flashcards --content "Your study material..." --num-cards 15

# Create a quiz
lmastudio study quiz --content "Your content..." --num-questions 10 --question-type "mixed"

# Create a glossary
lmastudio study glossary --content "Your content..."
```

## Chad Mode (Evidence-Based Q&A)

### Direct Questions
```bash
# Answer a specific question
lmastudio chad answer-question --question "What are the main tenets of behavioral economics?"

# Fact-check a statement
lmastudio chad fact-check --statement "Climate change is primarily caused by human activities"
```

## Coding

### Code Generation
```bash
# Generate a complete project
lmastudio coder code-project --requirements "Create a Python web scraper for news articles" --language "python"

# Fix code issues
lmastudio coder fix-code --code "Your buggy code..." --issue "Function not returning expected values"

# Review code
lmastudio coder review-code --code "Your code to review..." --language "javascript"
```

## Backend Configuration

### Switching Backends
```bash
# Set to bridge backend (default)
lmastudio backend set bridge

# Set to OpenRouter with specific model
lmastudio backend set openrouter --api-key "your-api-key" --model "openai/gpt-4o"

# Test current backend
lmastudio backend test
```

## Mode Toggles

### Conversation Modes
```bash
# Set to battle mode
lmastudio mode mode battle

# Set battle target to A
lmastudio mode battle-target A

# Enable tavern mode (merge system messages)
lmastudio mode tavern true

# Enable bypass mode
lmastudio mode bypass true
```

## Debugging and State Management

### Session Management
```bash
# Show current session state
lmastudio debug state

# Show current configuration
lmastudio debug config

# Save current session
lmastudio debug save-state ./session_backup.json

# Load a saved session
lmastudio debug load-state ./session_backup.json
```