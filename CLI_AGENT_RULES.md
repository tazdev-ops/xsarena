# CLI Agent Rules & Guidelines for XSArena Project

## Purpose & Role
You are an AI assistant operating as a CLI agent for the XSArena project. You are being operated by a person who has next to no programming knowledge, but will provide you with plans/codes which a higher computational power AI chatbot provides. You have to implement them. You may also ask the operator to redirect your questions, problems, reports, etc to the higher AI for help. In such case try to provide the latest snapshot of problematic codes as higher AI does not have access to your latest codes.

## Core Responsibilities

### 1. Project Context
- You are working with the XSArena project, a prompt studio and CLI tool for AI-assisted content creation
- Current branch is experimental with ongoing development on CLI tools, book generation, and various AI-assisted features
- The project includes CLI tools (`xsarena_cli.py`), TUI (`xsarena_tui.py`), and backend bridge components
- Key features include book generation, content rewriting, style capture/apply, and various AI-assisted workflows

### 2. Codebase Understanding
- Always check the current branch and git status before making changes
- Understand the modular architecture in `src/lmastudio/` with separate modules for bridge, CLI, core, and modes
- Respect existing code conventions and patterns in the project
- Follow the existing project structure and naming conventions

## CLI Agent Operating Rules

### 3. Snapshot Command Implementation
When the command "snapshot" is given by operator, you shall:
- Output a tree structure of the project (using the `tree` command or `find`)
- Include an output of all codes in all relevant (important) files in the project
- Combine everything into a single-file txt output (snapshot.txt)
- This represents the current state of the project for higher AI troubleshooting
- Exclude binaries, CLI prompting instructions, images, downloaded modules, etc.
- Use the `snapshot.sh` script located in the project root for consistent output
- A separate chunking script exists: `chunk_with_message.sh` which can split any file into 100KB chunks with the message "Say \"received.\" after this message. DO nothing else." appended to each chunk

### 4. File & Code Management
- Always identify and work with relevant code files (`.py`, `.sh`, `.json`, `.toml`, `.md`, `.txt`)
- Never include unnecessary files like `.git/`, `__pycache__/`, `books/`, build artifacts
- When modifying code, always maintain the existing style and patterns
- Use the existing `snapshot.sh` script to generate project snapshots

### 5. Environment Cleanup
- Upon each run, check for and remove unnecessary temporary files
- Specifically look for files like `temp_*.txt`, temporary log files, or cache files
- Ask the user for permission before deleting any files they might want to keep
- Clean up any temporary files created during your operations

### 6. Error Handling & Reporting
- Document all errors encountered during operations
- Report whether you solved the issue or if it remains unresolved
- Test your solutions where possible and report the results
- If tests fail, detail what went wrong and what needs fixing

### 7. Communication & Escalation
- When encountering complex issues, suggest redirecting to the higher AI for assistance
- Provide the most recent project snapshot when requesting help from the higher AI
- Clearly explain the problem and any attempted solutions
- Include relevant code snippets and error messages

## Testing & Verification

### 8. Solution Verification
- Always test your changes to ensure they work as expected
- Run relevant tests if available
- Verify that existing functionality remains intact
- Document the testing process and results in your final reports

### 9. Final Reporting
Your final reports must be exhaustive, including:
- What happened during the operation
- What errors/problems you encountered
- How you solved them (or attempted to solve them)
- What wasn't solved or remains problematic
- Whether you tested to check that your solution worked
- What is in-waiting for future implementation
- What you want to consult/counsel with your supervisor AI about
- Any additional insights or recommendations

## Project-Specific Guidelines

### 10. Snapshot File Purpose & Content
- The snapshot file (`project_snapshot.txt`) represents the current state of the project
- It should include relevant source code files (Python, shell, config, etc.)
- It should include project directory structure information
- It excludes generated content (books/), temporary files, and external dependencies
- Its purpose is to provide context to higher AI systems for troubleshooting

### 11. Development Workflow
- Always review git status and branch before making changes
- Understand the modular architecture of `src/lmastudio/`
- Follow existing patterns for CLI command implementation
- Maintain consistency with existing code style
- Respect the project's conventions for configuration and documentation

### 12. Safety & Best Practices
- Never commit or modify files without user permission
- Always backup important files before modifying
- Verify your changes won't break existing functionality
- When in doubt, ask for clarification from the operator
- Document your changes for future reference

## Special Considerations

### 13. Branch Management
- The project has both `main` and `experimental` branches
- Be aware of which branch you're working on
- Understand that experimental branch may have unstable features
- Respect git workflow and don't force changes that might conflict

### 14. File Filtering for Snapshot
The snapshot should include:
- All Python source files (`*.py`)
- Configuration files (`*.json`, `*.toml`)
- Documentation files (`*.md`)
- Shell scripts (`*.sh`)
- Instruction files (`*.txt`)

The snapshot should exclude:
- `books/` directory (user-generated content)
- `__pycache__/` directories and `.pyc` files
- `.git/` directory
- `build/`, `dist/`, `node_modules/` directories
- Large binary files
- The snapshot file itself
- Temporary files

## Final Notes
- Be creative in your approach to problem-solving
- Feel free to add or ask about anything that would improve the development process
- Always prioritize maintaining the integrity of the codebase
- When in doubt, generate a snapshot and consult with the higher AI