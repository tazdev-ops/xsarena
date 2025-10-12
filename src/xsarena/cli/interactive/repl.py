#!/usr/bin/env python3
"""
REPL functions extracted from interactive.py
"""

import asyncio
import sys
from typing import Dict

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    PTK_AVAILABLE = True
except ImportError:
    PTK_AVAILABLE = False


async def read_multiline(hint="Paste lines. End with: EOF", state: Dict = None):
    """Read multiline input from user."""
    print(hint)
    buf = []
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        if line.strip() == "EOF":
            break
        buf.append(line.rstrip("\n"))
    return "\n".join(buf)


async def repl(state: Dict):
    """Fallback REPL implementation."""
    help_text_func = state["help_text"]
    prompt_func = state["prompt"]
    _handle_command = state["_handle_command"]

    help_text_func()
    prompt_func()
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.rstrip("\n")
        if not line.strip():
            prompt_func()
            continue

        await _handle_command(line, state)
        prompt_func()


async def repl_prompt_toolkit(state: Dict):
    """Prompt Toolkit REPL implementation."""
    if not PTK_AVAILABLE:
        warn_func = state.get("warn", print)
        warn_func("prompt_toolkit not available. Falling back to simple input.")
        return await repl(state)

    session = PromptSession()
    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):  # Ctrl+C
        # Set cancel flag but don't exit the prompt - let the main loop handle it
        state["CANCEL_REQUESTED"] = True
        event.cli.exit()  # Exit current prompt to return control to main loop

    @kb.add("c-x")
    def _(event):  # Ctrl+X -> exit
        # Set a flag to indicate exit was requested via Ctrl+X
        state["PTK_CTRL_X_EXIT"] = True
        event.cli.exit()  # Exit the prompt session to return control to the main loop

    @kb.add("c-p")
    def _(event):  # Ctrl+P -> pause after current
        state["AUTO_PAUSE"] = True
        print("\n[set autopause ON]")

    @kb.add("c-s")
    def _(event):  # Ctrl+S -> /status
        print()
        asyncio.create_task(state["_handle_command"]("/status", state))

    help_text_func = state["help_text"]
    prompt_func = state["prompt"]

    help_text_func()
    prompt_func()
    while True:
        try:
            line = await session.prompt_async("> ", key_bindings=kb)
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C in prompt (if not handled by keybinding)
            # Check if exit was requested via Ctrl+X
            if state.get("PTK_CTRL_X_EXIT"):
                state.pop("PTK_CTRL_X_EXIT", None)
                raise SystemExit(0)  # Exit because of Ctrl+X
            elif state.get("CANCEL_REQUESTED"):
                state.pop(
                    "CANCEL_REQUESTED", None
                )  # Clear flag if it was set by keybinding
                continue
            raise SystemExit(0)

        if line is None:
            # This can happen when exit() is called on the prompt session
            if state.get("PTK_CTRL_X_EXIT"):
                # This was a Ctrl+X exit request
                state.pop("PTK_CTRL_X_EXIT", None)
                raise SystemExit(0)  # Exit properly
            elif state.get("CANCEL_REQUESTED"):
                # This was a Ctrl+C cancel request - just continue the loop
                state.pop("CANCEL_REQUESTED", None)
                continue
            continue
        elif state.get("PTK_CTRL_X_EXIT"):
            # Handle case where Ctrl+X was pressed and we have a line
            state.pop("PTK_CTRL_X_EXIT", None)
            raise SystemExit(0)
        elif state.get("CANCEL_REQUESTED"):  # Handle Ctrl+C cancel request
            state.pop("CANCEL_REQUESTED", None)  # Clear the flag
            raise SystemExit(0)  # This is for the exception handler case

        # Handle command/chat
        await state["_handle_command"](line, state)
        prompt_func()
