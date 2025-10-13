# XSArena Architecture Documentation

## Overview
XSArena is an AI-powered writing and coding studio that provides a command-line interface for various content creation tasks. The system is built with a modular architecture that separates concerns into distinct components.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI/TUI       │    │   Bridge Server  │    │ External AI     │
│   Interface     │◄──►│   (Local)        │◄──►│   Services      │
└─────────┬───────┘    └─────────┬────────┘    └─────────────────┘
          │                      │
          │              ┌───────▼────────┐
          │              │    Core        │
          │              │   Engine       │
          │              └───────┬────────┘
          │                      │
          └──────────────────────┼──────────────┐
                                 │              │
                    ┌────────────▼────────┐    │
                    │    Modes &          │    │
                    │   Functionality     │    │
                    │   (Book, Coder,     │    │
                    │   Study, etc.)      │    │
                    └─────────────────────┘    │
                                               │
                    ┌─────────────────────────┴──┐
                    │    Backends &              │
                    │   Configuration            │
                    │   (OpenRouter, Bridge,     │
                    │   etc.)                    │
                    └────────────────────────────┘
```

## Directory Structure

```
xsarena/
├── src/
│   └── xsarena/                 # Main package
│       ├── bridge/              # CSP-safe bridge server
│       │   ├── server.py        # Local bridge for AI services
│       │   └── compat_server.py # Compatibility server
│       ├── cli/                 # Command-line interface
│       │   ├── main.py          # Main CLI entry point
│       │   ├── core.py          # CLI core functionality
│       │   ├── service.py       # Service management
│       │   ├── cmds_*.py        # Command modules (book, backend, etc.)
│       │   └── interactive/     # Interactive features (REPL, etc.)
│       ├── core/                # Core engine and utilities
│       │   ├── engine.py        # Main communication engine
│       │   ├── backends.py      # Backend implementations
│       │   ├── state.py         # Session state management
│       │   ├── config.py        # Configuration management
│       │   ├── jobs.py          # Job management
│       │   ├── chunking.py      # Text chunking utilities
│       │   ├── templates.py     # System prompts and templates
│       │   └── ...              # Other core utilities
│       ├── modes/               # Different operational modes
│       │   ├── book.py          # Book authoring functionality
│       │   ├── chad.py          # Advanced content creation
│       │   ├── coder.py         # Code generation
│       │   ├── study.py         # Study and learning tools
│       │   ├── lossless.py      # Lossless text processing
│       │   └── bilingual.py     # Translation functionality
│       └── utils/               # Utility functions
├── directives/                  # System prompts and directives
├── recipes/                     # Predefined job specifications
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── books/                       # Generated content (excluded from git)
└── .xsarena/                    # Runtime state (excluded from git)
```

## Core Components

### 1. CLI Layer (`src/xsarena/cli/`)
The CLI layer provides the user interface for the system:

- **main.py**: Main entry point that registers all subcommands
- **cmds_*.py**: Individual command modules for different functionality areas
- **interactive/**: REPL, recipe handling, and other interactive features

### 2. Core Engine (`src/xsarena/core/`)
The core engine handles the communication and state management:

- **engine.py**: Main communication engine that manages AI interactions, continuation strategies, and post-processing
- **backends.py**: Abstracts different AI service providers (OpenRouter, bridge, etc.)
- **state.py**: Manages session state, history, and configuration settings
- **chunking.py**: Handles text chunking, anchoring, and continuation strategies
- **templates.py**: Contains system prompts and user prompt templates

### 3. Modes (`src/xsarena/modes/`)
Different operational modes provide specialized functionality:

- **book.py**: Book authoring with various styles (zero2hero, reference, popular science, etc.)
- **coder.py**: Code generation and modification
- **study.py**: Study and learning tools
- **lossless.py**: Lossless text processing
- **bilingual.py**: Translation and bilingual content creation
- **chad.py**: Advanced content creation modes

### 4. Bridge (`src/xsarena/bridge/`)
The bridge component handles communication with external AI services:

- **server.py**: CSP-safe local server that acts as an intermediary
- **compat_server.py**: Compatibility server for different API formats

## Key Features & Functionality

### 1. Book Authoring Modes
- **zero2hero**: Comprehensive books from basic to advanced concepts
- **reference**: Detailed reference-style content
- **pop**: Popular science writing style
- **nobs**: No-nonsense, direct content
- **outline**: Automatic outline generation
- **polish/shrink/critique**: Text refinement tools

### 2. Continuation Strategies
- **Anchor mode**: Uses text anchors for seamless continuation
- **Normal mode**: Standard continuation
- **Coverage hammer**: Prevents early conclusion in self-study modes
- **Output pushing**: Auto-extends within subtopics to meet length requirements

### 3. Repetition Handling
- **Detection**: Jaccard-based repetition detection
- **Warning**: Configurable thresholds for repetition alerts
- **Anti-repeat filtering**: Prevents redundant content generation

### 4. Backend Support
- **OpenRouter**: Integration with OpenRouter API
- **Bridge**: Local CSP-safe server for external AI services
- **Configurable**: Easy switching between different backends

### 5. Interactive Features
- **REPL**: Interactive command-line interface
- **Styles**: Predefined system prompts and styles
- **Recipes**: Predefined job specifications
- **Macros**: Command shortcuts and automation

## Configuration and State Management

### Session State (`src/xsarena/core/state.py`)
- **Continuation mode**: anchor vs normal
- **Output settings**: min chars, push passes, budget addendum
- **Repetition settings**: warning, threshold, n-gram size
- **History**: Message history with window management
- **Anchors**: Text anchors for continuation

### Configuration (`src/xsarena/core/config.py`)
- **Backend selection**: bridge vs openrouter vs other
- **Model selection**: Different AI models
- **API keys**: Secure key management
- **Window size**: History context management

## Workflow Patterns

### 1. Basic Book Creation
```
CLI Command → Mode Handler → Engine → Backend → Response Processing → Output
```

### 2. Interactive Session
```
REPL → Style/Recipe Loading → Command Execution → Engine → Backend → Continuation
```

### 3. Batch Processing
```
Recipe File → Job Runner → Multiple Engine Calls → Chunked Output → File Writing
```

## Extensibility Points

### Adding New Modes
1. Create a new mode class in `src/xsarena/modes/`
2. Add CLI commands in `src/xsarena/cli/cmds_modes.py`
3. Register in the main CLI application

### Adding New Backends
1. Implement the Backend interface in `src/xsarena/core/backends.py`
2. Add configuration options in `src/xsarena/core/config.py`

### Adding New CLI Commands
1. Create new command functions in appropriate `cmds_*.py` file
2. Register with Typer app
3. Add to main CLI registration in `main.py`

## Data Flow

1. **User Input**: Command-line arguments or REPL input
2. **Processing**: Mode handler processes the request
3. **Engine**: Core engine manages communication and state
4. **Backend**: AI service processes the request
5. **Response**: Engine processes and formats the response
6. **Output**: Result returned to user or saved to file

## Security Considerations

- **CSP-safe bridge**: Local server for secure AI service communication
- **API key management**: Secure handling of API keys
- **Content filtering**: Optional redaction filters
- **State isolation**: Per-session state management
