# LMArena CLI with Book Autopilot

This CLI tool allows you to create books using the LMArena AI with automated chunk-by-chunk generation using the "continue." command.

## Features

- **Book Autopilot Mode**: Automated book generation with auto-continue functionality
- **CSP-Safe Polling Bridge**: Works with browser extensions without WebSocket
- **File Output**: Writes content directly to files
- **Chunk Detection**: Recognizes "NEXT:" markers and stops at "NEXT: [END]"

## Requirements

- Python 3.7+
- aiohttp (`pip install aiohttp`)

## Setup

1. Install dependencies:
   ```bash
   ./install_deps.sh
   ```

2. Make sure you have the CSP-safe polling userscript installed in your browser and are on https://lmarena.ai

## Usage

1. Start the CLI:
   ```bash
   python lma_cli.py
   ```

2. In the CLI, capture your session IDs:
   ```
   /capture
   ```
   
3. Click "Retry" in LMArena to capture your IDs (they will be displayed in the CLI)

4. Load your directive file:
   ```
   /systemfile directives/psychology_manual.txt
   ```

5. Start the book autopilot:
   ```
   /book.start output/my_book.md
   ```

The system will automatically send "BEGIN", then continue with "continue." after each chunk until it receives "NEXT: [END]".

## Commands

- `/help` - Show all commands
- `/status` - Show current status and settings
- `/capture` - Capture session IDs from browser
- `/setids <sess> <msg>` - Set IDs manually
- `/systemfile <path>` - Load system directive from file
- `/book.start <outfile>` - Start autopilot mode
- `/book.stop` - Stop autopilot mode
- `/book.status` - Show autopilot status
- `/book.max <N>` - Limit number of chunks
- `/window <N>` - Set history window size
- `/mono` - Toggle monochrome output
- `/clear` - Clear chat history
- `/exit` - Quit the CLI

## Directives

The `directives/` folder contains sample directive files for different types of content. You can create your own directive files with specific instructions for the AI.

## Output

Generated content is saved to the specified output file with clean formatting (NEXT: markers are stripped from the saved text).

## Notes

- The tool maintains a rolling history of the last 40 exchanges by default
- If Cloudflare challenges appear, complete them in the browser and the process will continue
- The autopilot will stop automatically when the AI responds with "NEXT: [END]"