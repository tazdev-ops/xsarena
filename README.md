# LMASudio

AI-powered writing and coding studio

## Overview

LMASudio is a comprehensive tool for AI-assisted writing, coding, and content creation. It provides multiple modes for different types of work, from book authoring to code generation, all unified under a consistent engine.

## Features

- **Book Authoring Modes**: Create comprehensive books with zero2hero, reference, popular science, and no-bullshit manual styles
- **Lossless Processing**: Improve text while preserving all original meaning
- **Bilingual Processing**: Translate and align content between languages
- **Policy Analysis**: Generate and analyze policy documents
- **Study Tools**: Create flashcards, quizzes, and study guides
- **Chad Mode**: Evidence-based Q&A with blunt but safe responses
- **Coding Mode**: Full file system access for code generation and modification
- **Multiple Backends**: Support for local bridge and OpenRouter APIs

## Installation

```bash
pip install lmastudio
```

## Quick Start

```bash
# Start the bridge server (if using local backend)
python -m src.lmastudio.bridge.server

# Use the CLI to generate a book outline
lmastudio book outline "Machine Learning Fundamentals"

# Write a no-bullshit manual
lmastudio book nobs "Python for Beginners"
```

## Architecture

The project follows a modular architecture:

```
src/
├── lmastudio/
│   ├── core/           # Core functionality
│   │   ├── config.py   # Configuration management
│   │   ├── state.py    # Session state management
│   │   ├── chunking.py # Text chunking and anchor management
│   │   ├── templates.py # Prompt templates
│   │   ├── backends.py # Backend implementations
│   │   ├── engine.py   # Core engine
│   │   ├── jobs.py     # Job queue and management
│   │   └── tools.py    # File system and command tools
│   ├── modes/          # Different operational modes
│   │   ├── book.py
│   │   ├── lossless.py
│   │   ├── bilingual.py
│   │   ├── policy.py
│   │   ├── study.py
│   │   ├── chad.py
│   │   └── coder.py
│   ├── cli/            # Command line interface
│   │   ├── main.py
│   │   ├── cmds_*.py   # Command modules
│   └── bridge/         # CSP-safe bridge server
│       └── server.py
```

## Modes

### Book Authoring
- `zero2hero`: Comprehensive book from basic to advanced concepts
- `reference`: Detailed reference material
- `pop`: Popular science style
- `nobs`: No-nonsense manual
- `outline`: Generate detailed outlines

### Lossless Processing
- `ingest`: Synthesize information
- `rewrite`: Preserve all meaning while improving text
- `run`: Comprehensive processing run

### Coding
- Full file system access with safety sandbox
- Code generation, review, and debugging

## Backends

LMASudio supports two backends:

1. **Bridge Backend** (default): Communicates with a local server that handles API requests securely
2. **OpenRouter Backend**: Direct API calls to OpenRouter services

## Contributing

See `CONTRIBUTING.md` for details on how to contribute to this project.

## License

MIT