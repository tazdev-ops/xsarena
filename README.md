# XSArena

XSArena is a human writer workflow tool that bridges to LMArena for long-form content creation. It focuses on providing a structured approach to writing books, manuals, and other long-form content with AI assistance.

## Quick Start

- **Install**: `pip install -e ".[dev]"`
- **Start bridge**: `xsarena ops service start-bridge-v2`
- **First run**: `xsarena run book "Hello World" --length standard --span medium`

## Essential Workflows

### Book Authoring
Generate comprehensive books from zero to hero level with structured prompts:
```bash
# Create a book with default settings
xsarena run book "Machine Learning Fundamentals"

# Create a longer book with custom length and span
xsarena run book "Advanced Python Programming" --length long --span book

# Plan first, then write
xsarena run from-plan --subject "History of Rome"
```

### Interactive Mode
Start an interactive session for real-time collaboration:
```bash
xsarena interactive start
```

### Study Aids
Generate educational materials from your content:
```bash
# Create flashcards from a text file
xsarena study generate flashcards path/to/content.txt

# Generate a quiz
xsarena study generate quiz path/to/content.txt --num 20

# Create a glossary
xsarena study generate glossary path/to/content.txt
```

### Content Processing
Process and refine content with lossless operations:
```bash
# Rewrite text while preserving meaning
xsarena author lossless-rewrite "Your text here..."

# Improve flow and transitions
xsarena author lossless-improve-flow "Your text here..."

# Enhance structure with headings
xsarena author lossless-enhance-structure "Your text here..."
```

## Command Overview

XSArena is organized into semantic command groups:

- **`run`** - Book generation and long-form content creation
- **`study`** - Educational tools (flashcards, quizzes, glossaries)
- **`author`** - Content creation, ingestion, and style tools
- **`interactive`** - Interactive sessions and real-time collaboration
- **`ops`** - Operations, jobs, settings, and service management
- **`dev`** - Development tools and agent functionality
- **`analyze`** - Content analysis and insights

## Documentation

- [Getting Started](./docs/getting_started.md) - Installation and first steps
- [Workflows](./docs/workflows.md) - Zero-to-hero workflows and recipes
- [EPUB Translation](./docs/EPUB_TRANSLATION.md) - Complete guide to translating EPUB books
- [Configuration](./docs/configuration.md) - Settings and persistence
- [Full docs](./docs/) - Complete documentation directory
