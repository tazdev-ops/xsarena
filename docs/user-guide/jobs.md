# Jobs

Jobs are the core mechanism for content generation in XSArena. Each job represents a long-running task that generates content in chunks.

## Job Lifecycle

### Job States

- `PENDING`: Job is created but not yet started
- `RUNNING`: Job is actively generating content
- `DONE`: Job completed successfully
- `FAILED`: Job encountered an error and stopped
- `CANCELLED`: Job was manually cancelled
- `PAUSED`: Job is temporarily suspended

### Creating Jobs

Jobs are typically created through the `run` commands:

```bash
xsarena run book "Your Topic" --length long --span book
```

This creates a job that will generate a book with the specified parameters.

## Job Management Commands

### List Jobs

```bash
xsarena ops jobs ls
```

This shows all jobs with their current state and statistics.

### Job Details

```bash
xsarena ops jobs summary <job_id>
```

This provides detailed information about a specific job.

### Monitor Jobs

```bash
xsarena ops jobs follow <job_id>
```

This follows the job's progress in real-time.

### Control Jobs

- Pause: `xsarena ops jobs pause <job_id>`
- Resume: `xsarena ops jobs resume <job_id>`
- Cancel: `xsarena ops jobs cancel <job_id>`

## Job Resumption

XSArena supports job resumption, allowing you to continue from where a job left off.

### Automatic Resume Detection

When running a command that would create a job with an output path that already has a resumable job, XSArena will prompt you:

```bash
xsarena run book "My Topic" --out ./books/my_topic.final.md
# If a job exists for this output, you'll see:
# Resumable job exists for ./books/my_topic.final.md: <job_id>
# Use --resume to continue or --overwrite to start fresh.
```

### Explicit Resume Options

- `--resume`: Resume the existing job
- `--overwrite`: Start a new job regardless of existing jobs
- Default behavior: Ask interactively if TTY, auto-resume if non-interactive

## Job Events and Logging

Each job maintains an event log at `.xsarena/jobs/<job_id>/events.jsonl`. This log contains:

- Job state changes
- Chunk completion events
- Error events and retries
- Control messages (pause, resume, cancel)
- Performance metrics

View the log with:
```bash
xsarena ops jobs log <job_id>
```

## Job Scheduling

Jobs are scheduled based on concurrency limits defined in the configuration:

```yaml
scheduler:
  concurrency:
    total: 1      # Maximum total concurrent jobs
    bridge: 1     # Maximum concurrent bridge jobs
    openrouter: 1 # Maximum concurrent OpenRouter jobs
```

## Job Statistics

Job statistics include:

- Total chunks generated
- Number of retries
- Failover events
- Stalls (watchdog timeouts)

View statistics with:
```bash
xsarena ops jobs summary <job_id> --json
```

## Job Cloning

Clone existing jobs to create new ones with similar parameters:

```bash
xsarena ops jobs clone <job_id> --name "New Job Name"
```

This creates a new job with the same configuration as the original but with a fresh job ID.

## Job Cleanup

Remove old jobs to free up disk space:

```bash
xsarena ops jobs gc --days 30 --yes
```

This removes jobs older than 30 days.