"""Agent tool registry with decorator-based registration system."""

from typing import Callable, Dict, Optional

# Global registry for agent tools
AGENT_TOOLS: Dict[str, Callable] = {}


def register_tool(func: Optional[Callable] = None, *, name: Optional[str] = None):
    """
    Decorator to register agent tools in the global registry.

    Can be used with or without parentheses:
    - @register_tool
    - @register_tool(name="custom_name")
    """

    def decorator(f: Callable) -> Callable:
        tool_name = name or f.__name__
        AGENT_TOOLS[tool_name] = f
        return f

    if func is None:
        # Called with parentheses: @register_tool(...) or @register_tool
        return decorator
    else:
        # Called without parentheses: @register_tool
        return decorator(func)


# Simple tools that were in the original cmds_agent.py
@register_tool
def ask_user_tool(question: str) -> str:
    """Ask the user a question and return their response."""
    from rich.console import Console

    console = Console()
    console.print(f"[bold yellow]AGENT ASKS:[/bold yellow] {question}")
    return console.input("> ")


@register_tool
def finish_tool(summary: str) -> str:
    """Tool to explicitly finish the agent session with a summary."""
    from rich.console import Console

    console = Console()
    console.print(f"[bold green]Agent finished:[/bold green] {summary}")
    return f"Session finished with summary: {summary}"


# Import the existing tools from the tools module and register them
# We'll import and register them when the module is loaded
def _register_existing_tools():
    """Register tools from the existing tools module."""
    try:
        from . import tools

        # Register the basic file system tools
        register_tool(tools.list_dir)
        register_tool(tools.read_file)
        register_tool(tools.write_file)
        register_tool(tools.run_cmd)

        # Register the patch and search tools
        from .tools import apply_patch, run_tests, search_text

        register_tool(apply_patch)
        register_tool(run_tests)
        register_tool(search_text)

        # Register the ticket tools
        from .coder_tools import ticket_list, ticket_new, ticket_next

        register_tool(ticket_list)
        register_tool(ticket_new)
        register_tool(ticket_next)

        # Register the patch tools
        from .coder_tools import diff_file, patch_apply, patch_dry_run

        register_tool(patch_apply)
        register_tool(patch_dry_run)
        register_tool(diff_file)

    except ImportError:
        # If imports fail, that's OK - tools may not be available in all contexts
        pass


# Register the tools when the module is loaded
_register_existing_tools()
