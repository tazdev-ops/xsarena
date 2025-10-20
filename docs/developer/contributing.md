# Contributing

We welcome contributions to XSArena! This document outlines the process for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A GitHub account

### Setting Up Your Development Environment

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/xsarena.git
   cd xsarena
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Branch Management

1. Create a feature branch from the appropriate base branch:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-fix-name
   ```

2. Use descriptive branch names:
   - `feat/` for new features
   - `fix/` for bug fixes
   - `chore/` for maintenance tasks
   - `docs/` for documentation changes
   - `refactor/` for refactoring

### Making Changes

1. Follow the existing code style and patterns
2. Write clear, descriptive commit messages
3. Test your changes thoroughly
4. Update documentation as needed

### Commit Messages

Use conventional commits format:
- `feat: add new snapshot verification command`
- `fix: resolve import error in prompt module`
- `docs: update installation instructions`
- `refactor: restructure job execution logic`

## Code Quality

### Testing

Before submitting a pull request:
1. Run the existing tests to ensure they still pass
2. Add tests for new functionality when applicable
3. Verify that your changes don't break existing functionality

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write clear, descriptive variable and function names
- Keep functions focused and reasonably sized
- Add docstrings to public functions and classes

## Pull Request Process

1. Ensure your changes are complete and tested
2. Update documentation if needed
3. Squash commits if necessary to create a clean history
4. Submit a pull request to the main repository
5. Address any feedback from code review
6. Wait for approval before merging

## Development Guidelines

### Adding New Commands

When adding new CLI commands:

1. Create the command in the appropriate `cmds_*.py` file in `src/xsarena/cli/`
2. Register the command with the app instance
3. Add help text and appropriate options
4. Follow existing patterns for consistency
5. Test the command thoroughly

### Modifying Core Logic

When modifying core functionality:

1. Understand the existing architecture and dependencies
2. Make changes incrementally when possible
3. Preserve backward compatibility when feasible
4. Update related components if needed
5. Test thoroughly in different scenarios

### Error Handling

- Provide clear, actionable error messages
- Use appropriate exception types
- Log errors for debugging when appropriate
- Handle edge cases gracefully

## Documentation

### Code Documentation

- Add docstrings to new functions and classes
- Update existing documentation when changing functionality
- Use clear, concise language
- Include examples when helpful

### User Documentation

- Update command references when adding new features
- Add usage examples for new functionality
- Keep documentation synchronized with code changes

## Getting Help

If you need help with your contribution:

1. Check the existing documentation
2. Look at similar implementations in the codebase
3. Open an issue if you need clarification
4. Join the community discussions if available

## Code of Conduct

Please follow the project's code of conduct when participating in this project.
