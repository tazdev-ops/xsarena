"""A CLI-based AI coding agent that uses tools to accomplish goals."""

import asyncio
import json

import typer
from rich.console import Console

from ..core.agent_tools import AGENT_TOOLS
from .context import CLIContext

app = typer.Typer(help="AI coding agent with local file system access.")
console = Console()


def get_tool_system_prompt():
    """Generate the system prompt with available tools."""
    return """You are a local coding agent operating via tools. Return ONLY one JSON object per turn.

Available tools: {available_tools}

Schema:
{{
  "thought": "Briefly state your reasoning for the next action.",
  "plan": ["A short list of your immediate next steps."],
  "actions": [
    {{"tool":"list_dir","args":{{"path":"."}}}},
    {{"tool":"read_file","args":{{"path":"path/to/file.py"}}}},
    {{"tool":"write_file","args":{{"path":"path/to/new_file.py","content":"..."}}}},
    {{"tool":"run_cmd","args":{{"cmd":"pytest -q"}}}},
    {{"tool":"ask_user","args":{{"question":"What is the expected output?"}}}},
    {{"tool":"apply_patch","args":{{"path":"path/to/file.py","patch":"unified diff patch content"}}}},
    {{"tool":"search_text","args":{{"path":"path/to/search","query":"search term","regex":false}}}},
    {{"tool":"run_tests","args":{{"args":"-q"}}}},
    {{"tool":"ticket_new","args":{{"file":"path/to/file.py","lines":"10-20","note":"Fix the bug in function X"}}}},
    {{"tool":"ticket_next","args":{{}}}},
    {{"tool":"ticket_list","args":{{}}}},
    {{"tool":"patch_dry_run","args":{{"filepath":"path/to/file.py","patch":"unified diff patch content"}}}},
    {{"tool":"patch_apply","args":{{"filepath":"path/to/file.py","patch":"unified diff patch content"}}}},
    {{"tool":"diff_file","args":{{"filepath":"path/to/file.py"}}}},
    {{"tool":"finish","args":{{"summary":"..."}}}}
  ],
  "final": "A summary of what you did and how to verify it."
}}

Rules:
- Discover before editing. Use `list_dir` and `read_file`.
- Keep changes small and focused.
- When finished, provide a summary in the `final` field.
- When goal complete, MUST call finish tool with summary: {{"tool":"finish","args":{{"summary":"..."}}}}
- You are restricted to the project's root directory.
- `run_cmd` is limited to safe, development-related commands.
- Use `search_text` to find occurrences of strings or patterns in files.
- Use `apply_patch` to apply unified diff patches to files.
- Use `run_tests` to execute pytest with specified arguments.
- Use `ticket_new` to create coding tickets for future work.
- Use `ticket_next` to get the next pending ticket.
- Use `ticket_list` to see all tickets.
- Use `patch_dry_run` to preview what a patch would change before applying it.
- Use `patch_apply` to apply patches to files.
- Use `diff_file` to see the current diff of a file.
""".format(
        available_tools=", ".join(sorted(AGENT_TOOLS.keys()))
    )


@app.command("start")
def agent_start_sync(
    ctx: typer.Context,
    goal: str = typer.Argument(..., help="The high-level goal for the agent."),
    max_steps: int = typer.Option(20, "--steps", help="Maximum number of agent steps."),
):
    """Start an AI agent session to accomplish a coding goal."""
    asyncio.run(agent_start(ctx, goal, max_steps))


async def agent_start(
    ctx: typer.Context,
    goal: str = typer.Argument(..., help="The high-level goal for the agent."),
    max_steps: int = typer.Option(20, "--steps", help="Maximum number of agent steps."),
):
    """Start an AI agent session to accomplish a coding goal."""
    cli: CLIContext = ctx.obj
    console.print(f"[bold green]Starting agent with goal:[/bold green] {goal}")

    messages = [
        {"role": "system", "content": get_tool_system_prompt()},
        {"role": "user", "content": f"My goal is: {goal}\nBegin."},
    ]

    for step in range(1, max_steps + 1):
        console.print(f"\n[bold]--- Step {step}/{max_steps} ---[/bold]")

        # Prepare prompts for the engine
        system_prompt = messages[0]["content"]
        user_prompt = "\n".join(
            [m["content"] for m in messages[1:] if m["role"] == "user"]
        )

        response_text = await cli.engine.send_and_collect(
            user_prompt, system_prompt=system_prompt
        )
        messages.append({"role": "assistant", "content": response_text})

        try:
            import re

            # 1) Prefer fenced JSON
            fenced = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
            )
            json_text = fenced.group(1) if fenced else None
            # 2) Fallback: first { ... last }
            if not json_text:
                start, end = response_text.find("{"), response_text.rfind("}") + 1
                if start == -1 or end == 0:
                    raise ValueError("No JSON object found")
                json_text = response_text[start:end]
            # 3) Optional strict validation via pydantic (if installed)
            try:
                from pydantic import BaseModel

                class AgentTurn(BaseModel):
                    thought: str | None = None
                    plan: list[str] | None = None
                    actions: list[dict] | None = None
                    final: str | None = None

                parsed = AgentTurn.model_validate_json(json_text)
                parsed_json = parsed.model_dump()
            except Exception:
                parsed_json = json.loads(json_text)
            console.print(
                f"[italic]Thought: {parsed_json.get('thought', '...')}[/italic]"
            )

            if parsed_json.get("final"):
                console.print(
                    f"[bold green]Agent finished:[/bold green] {parsed_json['final']}"
                )
                break

            observations = []
            for action in parsed_json.get("actions", []):
                tool_name = action.get("tool")
                tool_args = action.get("args", {})
                if tool_name in AGENT_TOOLS:
                    console.print(f"Action: [cyan]{tool_name}({tool_args})[/cyan]")
                    try:
                        tool_func = AGENT_TOOLS[tool_name]
                        if tool_name == "finish":
                            # Special handling for finish tool - print summary and break
                            summary = tool_args.get(
                                "summary", "Agent session completed"
                            )
                            console.print(
                                f"[bold green]Agent finished:[/bold green] {summary}"
                            )
                            return  # Exit the function to terminate the agent session
                        if asyncio.iscoroutinefunction(tool_func):
                            result = await tool_func(**tool_args)
                        else:
                            result = tool_func(**tool_args)
                        observations.append({"tool": tool_name, "result": result})
                    except Exception as e:
                        observations.append({"tool": tool_name, "error": str(e)})
                else:
                    observations.append({"tool": tool_name, "error": "Unknown tool"})

            obs_text = json.dumps({"observations": observations}, indent=2)
            messages.append({"role": "user", "content": obs_text})

        except (json.JSONDecodeError, ValueError) as e:
            console.print(f"[bold red]Error parsing agent response:[/bold red] {e}")
            messages.append(
                {
                    "role": "user",
                    "content": "Your last response was not valid JSON. Please correct it and respond with ONLY a single, valid JSON object that follows the schema.",
                }
            )
            continue

    else:
        console.print(
            f"\n[bold yellow]Agent stopped after reaching max steps ({max_steps}).[/bold yellow]"
        )
