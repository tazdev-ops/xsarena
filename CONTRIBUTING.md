# Contributing to XSArena

Thank you for your interest in contributing to XSArena! This document outlines the process for contributing to this project.

## Development Setup

1. Fork and clone the repository
2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

- Follow Python's PEP 8 style guide
- Use type hints for all public functions
- Write docstrings for all modules, classes, and functions
- Keep functions small and focused

## Running Tests

```bash
pytest
```

## Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them with:

```bash
pip install pre-commit
pre-commit install
```

## Pull Request Process

1. Create a feature branch from the main branch
2. Add tests for your changes
3. Update documentation as needed
4. Ensure all tests pass
5. Submit a pull request with a clear description

## Architecture Guidelines

When adding features, follow the existing architecture:

- Core functionality in `src/lmastudio/core/`
- Modes in `src/lmastudio/modes/`
- CLI commands in `src/lmastudio/cli/`
- Backend implementations in `src/lmastudio/core/backends.py`

## Reporting Issues

Please include:
- A clear description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment information

## Questions?

Feel free to open an issue if you have questions about contributing.