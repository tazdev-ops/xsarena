#!/bin/bash
# Install dependencies for LMArena CLI with book autopilot

echo "Installing aiohttp dependency for LMArena CLI..."
pip3 install aiohttp

if [ $? -eq 0 ]; then
    echo "Installation successful!"
    echo ""
    echo "To use the book writing autopilot:"
    echo "1. Make sure your browser has the CSP-safe polling userscript installed and is open on https://lmarena.ai"
    echo "2. Run: python lma_cli.py"
    echo "3. In the CLI:"
    echo "   - /capture"
    echo "   - Click Retry on any message in LMArena (CLI should show IDs updated)"
    echo "   - /systemfile directives/general_book.txt  # or your directive file (replace [FIELD/TOPIC] with your subject)"
    echo "   - /book.start output/manual.psychology.md"
    echo ""
    echo "The autopilot will send BEGIN, write chunk 1 to the file, then auto-send 'continue.' and keep writing until NEXT: [END]"
else
    echo "Installation failed. Please install manually with: pip3 install aiohttp"
fi