# XSArena Snapshot Guide (Simplified)

## Overview
XSArena snapshots create comprehensive, flat representations of your project for sharing with AI systems or for backup purposes. They package your project files into a single text file or zip archive.

## Three-Tier Snapshot System

### 1. Minimal (Flat Text - Recommended for AI)
- **Command**: `xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map`
- **Output**: `~/repo_flat.txt`
- **Purpose**: For sharing with AI assistants
- **Features**: Redaction on by default, strict size limits

### 2. Normal (Zip Archive - For General Use)
- **Command**: `xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip`
- **Output**: `~/xsa_snapshot.zip`
- **Purpose**: For most other sharing needs
- **Features**: Compressed format, includes source files

### 3. Maximal (Debug Report - For Troubleshooting)
- **Command**: `xsarena ops snapshot debug-report`
- **Output**: `~/xsa_debug_report.txt`
- **Purpose**: For comprehensive debugging
- **Features**: Includes system info, logs, and project state

## Configuration (.snapshot.toml)

The `.snapshot.toml` file defines snapshot modes and file inclusion/exclusion rules:

```toml
max_size = 180000  # per file cap for write_text_snapshot

[modes.tight]
include = [
  ".snapshot.toml",
  "README.md",
  "COMMANDS_REFERENCE.md",
  "pyproject.toml",
  "src/xsarena/cli/main.py",
  # ... (other essential files)
]
exclude = [
  ".git/**", ".svn/**", ".hg/**", ".idea/**", ".vscode/**",
  "venv/**", ".venv/**", "__pycache__/**",
  # ... (other exclusions)
]
```

## Best Practices

1. **Verify Before Sharing**: Always run verification before sharing snapshots
   ```bash
   xsarena ops snapshot verify --file ~/repo_flat.txt
   ```

2. **Regular Snapshots**: Create snapshots before major changes

3. **Size Management**: If snapshots are too large, use more restrictive modes or add exclusions

4. **Security**: Redaction is enabled by default to protect sensitive information

## Key Commands Reference

### Creating Snapshots
```bash
# Minimal (recommended for AI)
xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map

# Normal
xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip

# Debug report
xsarena ops snapshot debug-report
```

### Verification
```bash
# Verify snapshot quality
xsarena ops snapshot verify --file ~/repo_flat.txt
```

## Troubleshooting

### Snapshot Too Large
1. Use ultra-tight mode: `--mode ultra-tight`
2. Add exclusions: `-X "books/**" -X "review/**"`
3. Reduce size limits: `--total-max 2000000`

### Missing Files
1. Use maximal mode: `--mode maximal`
2. Add specific files: `--mode custom -I path/to/file`
3. Check exclude patterns aren't too broad

### Secrets Detected
1. Run secret scanner: `xsarena ops health scan-secrets --path .`
2. Remove secrets from code
3. Ensure redaction is enabled (default)
