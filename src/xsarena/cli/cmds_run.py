from __future__ import annotations

import typer

from .cmds_run_advanced import (
    run_from_plan,
    run_from_recipe,
    run_lint_recipe,
    run_replay,
    run_template,
)
from .cmds_run_continue import run_continue
from .cmds_run_core import run_book, run_write

app = typer.Typer(help="Run a book or recipe in authoring mode")

# Add commands to the app
app.command("book")(run_book)
app.command("from-recipe")(run_from_recipe)
app.command("lint-recipe")(run_lint_recipe)
app.command("from-plan")(run_from_plan)
app.command("replay")(run_replay)
app.command("continue")(run_continue)
app.command("write")(run_write)
app.command("template")(run_template)
