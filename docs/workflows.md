# Common Workflows

This document describes common workflows and best practices for using XSArena effectively.

## Getting Started Workflow

### 1. Project Setup
```bash
# Initialize a new project
xsarena project init

# Start the bridge server
xsarena service start-bridge-v2

# Install the userscript in your browser
# Navigate to LMArena and capture session IDs
xsarena interactive
/capture
```

### 2. First Book Generation
```bash
# Run a simple book
xsarena run book "Introduction to Machine Learning"

# Or use interactive mode for more control
xsarena interactive
/run.book "Advanced Python Techniques" --profile clinical-masters
```

## Advanced Authoring Workflows

### 1. Planning-First Approach
```bash
# Start with a plan
xsarena run from-plan --subject "Deep Learning Handbook"

# The system will open an editor for you to enter rough seeds:
# 1) neural networks basics
# 2) backpropagation algorithm
# 3) convolutional networks
# 4) recurrent networks
# 5) transformer architectures
```

### 2. Iterative Development
```bash
# Start with a short run to test approach
xsarena run book "Topic" --length standard --span medium

# Continue and expand based on results
xsarena run continue ./books/topic.final.md --length long

# Use interactive mode for fine-tuning
xsarena interactive
/out.minchars 5000
/cont.mode anchor
/run.book "Refined Topic" --profile compressed
```

### 3. Style and Directive Management
```bash
# List available directives
xsarena directives list

# Use specific style overlays
xsarena run book "Topic" --profile clinical-masters

# Create custom directive combinations
xsarena directives booster
```

## Job Management Workflows

### 1. Batch Processing
```bash
# Submit multiple jobs with different priorities
xsarena run book "Urgent Topic" --priority 10
xsarena run book "Standard Topic" --priority 5
xsarena run book "Background Topic" --priority 1

# Monitor all jobs
xsarena jobs ls

# Boost a job's priority
xsarena jobs boost <job_id> --priority 9
```

### 2. Long-Running Projects
```bash
# Start a long book with automatic continuation
xsarena run book "Comprehensive Guide" --span book

# Check progress
xsarena jobs status <job_id>

# If a job stalls, resume it
xsarena run continue ./books/comprehensive_guide.final.md --until-end
```

## Quality and Reproducibility Workflows

### 1. Reproducible Runs
```bash
# Generate a run manifest
xsarena run book "Topic" --follow

# Replay a previous run from manifest
xsarena run replay ./books/topic.manifest.json --follow

# Lock directives to ensure consistency
xsarena project lock-directives
```

### 2. Content Analysis
```bash
# Analyze book coverage against outline
xsarena analyze coverage --outline outline.md --book book.final.md

# Check for continuity issues
xsarena analyze continuity

# Lint directive files
xsarena analyze style-lint directives/

# Extract checklists for review
xsarena tools extract-checklists --book book.final.md
```

## Configuration Workflows

### 1. Persistent Settings
```bash
# Adjust output settings for current session
xsarena settings minchars 5000
xsarena settings passes 4

# Persist these settings to project config
xsarena settings persist

# Reset to project defaults
xsarena settings reset
```

### 2. Multiple Endpoints
```bash
# Create endpoints.yml for different models/providers
xsarena run book "Topic" --endpoint gpt4_turbo
xsarena run book "Topic" --endpoint claude_opus
```

## Debugging and Troubleshooting

### 1. Job Issues
```bash
# Check job logs when something goes wrong
xsarena jobs log <job_id>

# See detailed job summary
xsarena jobs summary <job_id>

# Cancel a problematic job
xsarena jobs cancel <job_id>
```

### 2. Bridge Issues
```bash
# Check bridge health
curl http://127.0.0.1:5102/health

# Restart bridge service if needed
xsarena service stop bridge
xsarena service start bridge
```

## Best Practices

1. **Start Small**: Begin with standard length runs to test your approach before committing to longer works.

2. **Use Profiles**: Leverage predefined profiles for different content types and styles.

3. **Monitor Progress**: Use the jobs system to track long-running operations.

4. **Lock Directives**: For important projects, lock directive files to ensure reproducibility.

5. **Persist Settings**: Save your preferred configuration to avoid reconfiguring for each session.

6. **Plan First**: For complex topics, use the `from-plan` workflow to structure your content first.

7. **Analyze Results**: Use analysis tools to evaluate and improve your content quality.
