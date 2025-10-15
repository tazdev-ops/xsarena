# XSArena Concept

## Mission
XSArena is designed as a human writer workflow tool that bridges to LMArena for long-form content creation. The core concept is to provide a structured, human-in-the-loop approach to AI-assisted writing, focusing on long-form content like books, manuals, and documentation.

## Human-Focused Workflow
- XSArena puts the human writer in control of the process
- The AI serves as an intelligent assistant for content generation
- Writers maintain creative control while leveraging AI for research, drafting, and expansion
- Iterative refinement through anchor-based continuation

## Bridge-First Architecture
- All communication with LMArena happens through a secure bridge
- The bridge handles session management and message routing
- CSP-safe polling ensures secure communication without CORS issues
- Session and message IDs are managed through the bridge

## Single Canonical Run Path
- `xsarena run book` is the primary interface for all book generation
- Other commands (`fast`, `quick`, `plan`, `mixer`) are wrappers or deprecated
- Centralized configuration through `.xsarena/config.yml`
- Consistent parameter handling across all run modes

## Internal Agent Notes
For advanced users and development workflows, see `docs/INTERNAL_AGENT_NOTES.md`. These features are primarily for internal operator use and not required for normal human writer workflows.