# LMASudio

AI-powered writing and coding studio

## Overview

LMASudio is a comprehensive tool for AI-assisted writing, coding, and content creation. It provides multiple modes for different types of work, from book authoring to code generation, all unified under a consistent engine. The tool maintains compatibility with OpenAI-style APIs while adding powerful authoring capabilities.

## Features

- **Book Authoring Modes**: Create comprehensive books with zero2hero, reference, popular science, and no-bullshit manual styles
- **Lossless Processing**: Improve text while preserving all original meaning
- **Bilingual Processing**: Translate and align content between languages with alignment checking
- **Policy Analysis**: Generate and analyze policy documents with compliance scoring
- **Study Tools**: Create flashcards, quizzes, and study guides with spaced repetition
- **Chad Mode**: Evidence-based Q&A with blunt but safe responses and batch processing
- **Coding Mode**: Full file system access for code generation and modification
- **Multiple Backends**: Support for local bridge and OpenRouter APIs with cost estimation
- **OpenAI-Compatible API**: /v1 endpoints for SDK compatibility
- **Mode Toggles**: Direct/battle modes, tavern mode, bypass mode
- **Job Queue**: Run multiple long jobs sequentially with crash recovery
- **Watch Mode**: Automatically process new/updated files in a directory
- **Persistent State**: Session settings and history persistence

## Installation

```bash
pip install lmastudio
```

## Quick Start

```bash
# Start the bridge server (if using local backend)
python -m src.lmastudio.bridge.server

# Or start the compatibility server (OpenAI-compatible API)
python -m src.lmastudio.bridge.compat_server

# Use the CLI to generate a book outline
lmastudio book outline "Machine Learning Fundamentals"

# Write a no-bullshit manual
lmastudio book nobs "Python for Beginners"

# For complete examples, see: examples/commands.md
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
│   └── bridge/         # CSP-safe bridge server and compatibility API
│       ├── server.py
│       └── compat_server.py
```

## Modes

### Book Authoring
- `zero2hero`: Comprehensive book from basic to advanced concepts
- `reference`: Detailed reference material
- `pop`: Popular science style
- `nobs`: No-nonsense manual
- `outline`: Generate detailed outlines
- `polish`: Tighten prose, remove repetition, fix flow
- `shrink`: Condense to 70% length while preserving facts
- `diagram`: Generate Mermaid diagrams

### Lossless Processing
- `ingest`: Synthesize information
- `rewrite`: Preserve all meaning while improving text
- `run`: Comprehensive processing run
- `improve-flow`: Enhance transitions and readability
- `break-paragraphs`: Split dense text
- `enhance-structure`: Add headings and formatting

### Coding
- Full file system access with safety sandbox
- Code generation, review, debugging, and feature addition

## OpenAI-Compatible API

LMASudio provides a compatibility server that exposes OpenAI-style endpoints:

```bash
# Start the compatibility server
python -m src.lmastudio.bridge.compat_server --host 0.0.0.0 --port 8000

# Use with any OpenAI-compatible SDK
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Endpoints:
- `POST /v1/chat/completions` - Chat completions
- `GET /v1/models` - List available models

## Backends

LMASudio supports two backends:

1. **Bridge Backend** (default): Communicates with a local server that handles API requests securely
2. **OpenRouter Backend**: Direct API calls to OpenRouter services with model cost estimation

## Examples

For complete usage examples, see `examples/commands.md` which contains ready-to-use commands for:
- Nietzsche and Marx study guides
- Bilingual translation workflows
- Policy document generation
- Coding projects
- Chad mode Q&A sessions
- And more!

## Contributing

See `CONTRIBUTING.md` for details on how to contribute to this project.

## License

MIT