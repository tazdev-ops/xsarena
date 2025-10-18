# XSArena Architecture

This document provides an overview of the XSArena system architecture and its main components.

## Core Components

### 1. CLI Layer
The Command Line Interface serves as the primary user interaction point with semantic command groups:
- `author`: Core content creation workflows
- `analyze`: Analysis, reporting, and evidence-based tools
- `study`: Study aids, learning tools, and practice drills
- `dev`: Coding agent, simulation, and automation pipelines
- `ops`: System health, jobs, services, and configuration
- `project`: Project management and initialization
- `directives`: Directive tools and configuration

### 2. Orchestrator
The orchestrator manages the entire run process:
- Handles run specifications (RunSpecV2)
- Manages job submission and execution
- Generates run manifests for reproducibility
- Coordinates with the job scheduler

### 3. Job System
The job system handles asynchronous task execution:
- Job queue with priority support
- Concurrency control with backend-specific limits
- Resumable job execution
- Event logging and monitoring

### 4. Backends
Multiple backend support for different execution environments:
- `bridge`: Connects to LMArena through browser userscript
- `openrouter`: Direct API access to OpenRouter models
- `null`: Offline simulation for testing

### 5. Bridge Server
The bridge server facilitates communication with LMArena:
- WebSocket connection to browser userscript
- OpenAI-compatible API interface
- Cloudflare challenge handling
- Session ID management

## Data Flow

1. **CLI Input** → Command parsing and validation
2. **RunSpec Creation** → Specification object with parameters
3. **Orchestrator** → Job creation and scheduling
4. **Backend Selection** → Route to appropriate execution backend
5. **Execution** → Process through selected backend
6. **Output** → Write results to specified files
7. **Events** → Log all events to job-specific files

## Configuration Hierarchy

Configuration follows this precedence order:
1. Default values
2. `.xsarena/config.yml` settings
3. Session state from `.xsarena/session_state.json`

This allows for both persistent project defaults and dynamic session overrides.
