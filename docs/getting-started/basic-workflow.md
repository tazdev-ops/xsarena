# Basic Workflow

## Understanding the Core Concepts

XSArena uses a job-based system for content generation with the following key concepts:

- **Jobs**: Long-running content generation tasks
- **Chunks**: Individual segments of content generated in sequence
- **Continuation**: Methods to continue from where you left off
- **System Prompts**: Instructions that guide AI behavior

## Standard Workflow

### 1. Plan Your Content
Before generating content, consider:
- Topic and scope
- Desired length (standard, long, very-long, max)
- Span (medium, long, book)
- Style preferences (narrative, compressed, etc.)

### 2. Generate Content
Use the `run book` command to start content generation:

```bash
xsarena run book "Your Topic" --length long --span book
```

### 3. Monitor Progress
Check job status:
```bash
xsarena ops jobs ls
xsarena ops jobs status <job_id>
xsarena ops jobs follow <job_id>
```

### 4. Continue or Refine
- Use `run continue` to extend existing content
- Use `run from-plan` to generate from structured outlines
- Use `run from-recipe` to run from configuration files

## Job Management

### Job States
- `PENDING`: Job is queued
- `RUNNING`: Job is actively generating content
- `DONE`: Job completed successfully
- `FAILED`: Job encountered an error
- `CANCELLED`: Job was manually cancelled

### Job Controls
- `xsarena ops jobs pause <job_id>`: Pause a running job
- `xsarena ops jobs resume <job_id>`: Resume a paused job
- `xsarena ops jobs cancel <job_id>`: Cancel a job
- `xsarena ops jobs clone <job_id>`: Create a copy of a job

## Content Continuation

XSArena supports multiple continuation modes:
- **Anchor**: Continue from the end of existing content
- **Strict**: Continue with strict adherence to context
- **Off**: No continuation logic

The anchor mode is recommended for most use cases.
