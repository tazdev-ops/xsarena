# Snapshots

Snapshots are a core feature of XSArena that create comprehensive, flat representations of your project for sharing with AI systems or for backup purposes.

## Overview

Snapshots package your project files into a single text file, making it easy to share the entire project state with AI assistants or for backup purposes.

## Creating Snapshots

### Recommended Command

Use the `create` command for the recommended flat format:

```bash
xsarena ops snapshot create --mode author-core
```

This creates a snapshot optimized for AI assistants.

### Available Modes

- `author-core`: Essential files for AI authoring (recommended)
- `ultra-tight`: Minimal files for quick sharing
- `normal`: Standard project files
- `maximal`: Most project files including documentation
- `custom`: User-defined file selection

### Custom Snapshots

Create custom snapshots with specific files:

```bash
xsarena ops snapshot create --mode custom -I src/xsarena/core/prompt.py -I README.md
```

## Snapshot Modes

### Author-Core Mode

The recommended mode for AI interactions:

```bash
xsarena ops snapshot create --mode author-core --out ~/repo_flat.txt
```

Includes essential source files for development and AI authoring.

### Ultra-Tight Mode

For minimal, focused snapshots:

```bash
xsarena ops snapshot create --mode ultra-tight
```

Includes only the most critical files.

## Advanced Options

### File Size Limits

Control file and total sizes:

```bash
xsarena ops snapshot create \
  --mode author-core \
  --max-per-file 200000 \
  --total-max 4000000
```

### Include/Exclude Patterns

Fine-tune what's included:

```bash
xsarena ops snapshot create \
  --mode custom \
  -I "src/**/*.py" \
  -X "tests/**" \
  -X "*.pyc"
```

### Redaction

Enable automatic redaction of sensitive information:

```bash
xsarena ops snapshot create --redact
```

Redaction is enabled by default.

## Verification

Verify snapshot quality before sharing:

```bash
xsarena ops snapshot verify --file ~/repo_flat.txt
```

This checks for:
- Secrets in files
- Oversized files
- Disallowed file types
- Missing required files

## Debug Reports

For troubleshooting, create comprehensive debug reports:

```bash
xsarena ops snapshot debug-report
```

This includes system information, job logs, and detailed project state.

## Best Practices

### Regular Snapshots

Create snapshots before major changes:

```bash
xsarena ops snapshot create --mode author-core
```

### Sharing with AI

When sharing with AI assistants, use the author-core mode:

```bash
xsarena ops snapshot create --mode author-core --out ~/project_context.txt
```

### Verification Before Sharing

Always verify snapshots before sharing:

```bash
xsarena ops snapshot verify --file ~/project_context.txt --fail-on secrets
```

## Legacy Commands

The following legacy commands are deprecated but still available:

- `xsarena ops snapshot legacy-write` - Legacy snapshot command
- `xsarena ops snapshot legacy-txt` - Legacy flat pack command  
- `xsarena ops snapshot legacy-simple` - Legacy simple command

These are hidden by default and should not be used for new projects.

## Troubleshooting

### Snapshot Too Large

If your snapshot exceeds size limits:

1. Use a more restrictive mode: `--mode ultra-tight`
2. Add exclusions: `-X "books/**" -X "review/**"`
3. Reduce total size: `--total-max 2000000`

### Missing Files

If important files are missing:

1. Use `--mode maximal` for broader inclusion
2. Add specific files with `--mode custom -I path/to/file`
3. Check exclude patterns aren't too broad