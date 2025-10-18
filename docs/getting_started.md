# Getting Started with XSArena

Welcome to XSArena, an AI-powered writing and coding studio. This guide will help you get up and running quickly.

## Installation

XSArena is a Python package that can be installed with pip:

```bash
pip install xsarena
```

Or install from source:

```bash
git clone https://github.com/your-username/xsarena.git
cd xsarena
pip install -e .
```

## Quick Start

1. **Initialize a project:**
   ```bash
   xsarena project init
   ```

2. **Start the bridge server:**
   ```bash
   xsarena service start-bridge-v2
   ```

3. **Install the userscript:**
   Copy the `xsarena_bridge.user.js` file to your browser userscript manager (Tampermonkey/Violentmonkey).

4. **Capture session IDs:**
   In the interactive session, use `/capture` to capture session and message IDs from the LMArena website.

5. **Start authoring:**
   ```bash
   xsarena run book "Your Subject"
   ```

## Interactive Mode

For a more hands-on experience, use the interactive mode:

```bash
xsarena interactive
```

This opens a REPL-like interface where you can:
- `/run.book "Subject"` - Start a new book
- `/continue ./books/file.final.md` - Continue writing
- `/out.minchars 4500` - Set minimum output characters
- `/cont.mode anchor` - Set continuation mode
- `/capture` - Capture session IDs from browser
- `/config.show` - Show current configuration

## Configuration

XSArena uses a hierarchical configuration system:
1. Default values
2. `.xsarena/config.yml` settings
3. Session state from `.xsarena/session_state.json`

To persist session settings to the config file:
```bash
xsarena settings persist
```

To reset session settings from the config file:
```bash
xsarena settings reset
```
