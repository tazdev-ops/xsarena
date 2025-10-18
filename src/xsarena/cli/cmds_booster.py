"""CLI commands for the Prompt Booster."""

import json
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Interactively engineer and improve prompts.")
console = Console()

BOOSTER_STATE_FILE = Path(".xsarena/booster_state.json")


@app.command("start")
def booster_start(
    ctx: typer.Context,
    goal: str = typer.Argument(..., help="The goal for the new prompt."),
):
    """Start a new prompt boosting session."""
    # This is a simplified implementation. A full version would interact with the AI.
    console.print(f"Starting booster session for goal: '{goal}'")
    state = {
        "goal": goal,
        "status": "pending_questions",
        "questions": [
            "What is the target audience?",
            "What is the desired output format?",
        ],
    }
    BOOSTER_STATE_FILE.parent.mkdir(exist_ok=True)
    BOOSTER_STATE_FILE.write_text(json.dumps(state, indent=2))
    console.print(
        "[yellow]Booster has questions for you. Use 'xsarena booster answer' to respond.[/yellow]"
    )
    for q in state["questions"]:
        console.print(f"- {q}")


@app.command("answer")
def booster_answer(ctx: typer.Context):
    """Provide answers to the booster's questions."""
    if not BOOSTER_STATE_FILE.exists():
        console.print(
            "[red]No active booster session. Start one with 'xsarena booster start'.[/red]"
        )
        raise typer.Exit(1)

    state = json.loads(BOOSTER_STATE_FILE.read_text())
    answers = {}
    for q in state["questions"]:
        answers[q] = console.input(f"[cyan]{q}[/cyan]\n> ")

    state["answers"] = answers
    state["status"] = "ready_to_apply"
    state[
        "final_prompt"
    ] = f"// Generated Prompt based on goal: {state['goal']}\nSystem: You are a helpful assistant for {state['answers']['What is the target audience?']}. Your output format should be {state['answers']['What is the desired output format?']}."
    BOOSTER_STATE_FILE.write_text(json.dumps(state, indent=2))
    console.print(
        "[green]Answers received. A new prompt has been generated. Use 'xsarena booster apply' to use it.[/green]"
    )


@app.command("apply")
def booster_apply(
    ctx: typer.Context,
    target_file: str = typer.Argument(..., help="Path to save the new system prompt."),
):
    """Apply the generated prompt to a file."""
    if (
        not BOOSTER_STATE_FILE.exists()
        or json.loads(BOOSTER_STATE_FILE.read_text()).get("status") != "ready_to_apply"
    ):
        console.print(
            "[red]No generated prompt to apply. Complete the 'start' and 'answer' steps first.[/red]"
        )
        raise typer.Exit(1)

    state = json.loads(BOOSTER_STATE_FILE.read_text())
    Path(target_file).write_text(state["final_prompt"])
    console.print(f"[green]Prompt successfully applied to '{target_file}'.[/green]")
    BOOSTER_STATE_FILE.unlink()  # Clean up state
