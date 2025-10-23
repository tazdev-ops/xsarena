# XSArena

XSArena is a human writer workflow tool that bridges to LMArena for long-form content creation. It focuses on providing a structured approach to writing books, manuals, and other long-form content with AI assistance.

## Quick Start

- **Install**: `pip install -e ".[dev]"`
- **Start bridge**: `xsarena ops service start-bridge-v2`
- **First run**: `xsarena run book "Hello World" --length standard --span medium`

## Backend Configuration

### Bridge Setup (Default)
The default backend connects to a local bridge server:
- **Default URL**: `http://127.0.0.1:5102/v1`
- **Start service**: `xsarena ops service start-bridge-v2`
- **Capture IDs**: Use `xsarena settings capture-ids` or `/capture` in interactive mode
- **Authentication**: Requires internal token for `/internal/*` endpoints (see below)

### OpenRouter Setup
To use OpenRouter as a backend:
- **Environment variable**: `export OPENROUTER_API_KEY=your_api_key_here`
- **Default URL**: `https://openrouter.ai/api/v1` (override with `OPENROUTER_BASE_URL`)
- **Test connection**: `xsarena ops config backend-test`
- **Usage**: `xsarena tools eli5 "Photosynthesis"` or any other command

### Internal Token Authentication
The bridge uses an internal token for `/internal/*` endpoints:
- **Environment variable**: `export XSA_INTERNAL_TOKEN=dev-token-change-me`
- **Config file**: Add `bridge.internal_api_token` in `.xsarena/config.yml`
- **Default**: `dev-token-change-me` (change for production)

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

- [Getting Started](./docs/USAGE.md) - Installation and first steps
- [Workflows](./docs/USAGE.md) - Zero-to-hero workflows and recipes
- [Configuration](./docs/OPERATING_MODEL.md) - Settings and persistence
- [Full docs](./docs/) - Complete documentation directory
