# First Run

## Initial Setup

After installing XSArena, follow these steps to get started:

### 1. Verify Installation

```bash
xsarena --help
```

### 2. Run Health Check

```bash
xsarena ops health fix-run
```

### 3. Configure Backend

Choose your preferred backend:

#### Bridge Backend (Recommended)
1. Start the bridge server: `xsarena ops service start-bridge-v2`
2. Open https://lmarena.ai with `#bridge=5102` in the URL
3. Install the userscript in Tampermonkey/Greasemonkey

#### OpenRouter Backend
1. Get an API key from OpenRouter
2. Configure in `.xsarena/config.yml` or via CLI: `xsarena backend openrouter`

### 4. Create Your First Book

```bash
xsarena run book "Your Topic Here"
```

## Quick Start Examples

### Generate a Book
```bash
xsarena run book "Machine Learning Fundamentals" --length long --span book
```

### Continue an Existing Book
```bash
xsarena run continue path/to/book.md --until-end
```

### Create a Snapshot
```bash
xsarena ops snapshot create --mode author-core
```

## Common First Steps

1. **Check system status**: `xsarena ops health fix-run`
2. **View available commands**: `xsarena --help`
3. **Test backend connectivity**: `xsarena backend ping`
4. **Generate your first content**: `xsarena run book "Hello World"`