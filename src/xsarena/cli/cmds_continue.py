from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import asyncio
import typer

from .context import CLIContext
from ..core.prompt import compose_prompt
from ..core.chunking import anchor_from_text
from ..core.specs import LENGTH_PRESETS, SPAN_PRESETS, DEFAULT_PROFILES

app = typer.Typer(help="Continue writing an existing book from its tail (anchor).")

def _read_tail_anchor(p: Path, tail_chars: int) -> str:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    return anchor_from_text(txt, tail_chars)

async def _seed_and_continue(cli: CLIContext, book_path: Path, system_text: str, init_chunks: Optional[int], min_chars: int, passes: int):
    st = cli.state
    st.session_mode = "zero2hero"
    st.output_min_chars = min_chars
    st.output_push_max_passes = passes
    st.output_budget_snippet_on = True
    cli.save()

    anchor = _read_tail_anchor(book_path, st.anchor_length)
    seed_user = (await cli.engine.build_anchor_continue_prompt(anchor)) if anchor else "Continue."
    first = await cli.engine.send_and_collect(seed_user, system_prompt=system_text)
    with book_path.open("a", encoding="utf-8") as f:
        if not first.startswith("\n"):
            f.write("\n\n")
        f.write(first.strip())

    # Auto loop
    if init_chunks is None:
        await cli.engine.autopilot_run(initial_prompt="BEGIN", max_chunks=None)  # until model emits NEXT: [END]
    else:
        remaining = max(0, init_chunks - 1)
        if remaining > 0:
            await cli.engine.autopilot_run(initial_prompt="BEGIN", max_chunks=remaining)

@app.command("start")
def continue_start(
    ctx: typer.Context,
    book_file: str = typer.Argument(..., help="Existing book file to continue (e.g., ./books/finals/subject.final.md)"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Subject title (if different from filename)"),
    length: str = typer.Option("long", "--length", help="Per-message length: standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="Total span: medium|long|book (ignored if --until-end)"),
    profile: str = typer.Option("", "--profile", help="Preset: clinical-masters|elections-focus|compressed-handbook|pop-explainer|bilingual-pairs"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E", help="Append file content(s) to system prompt (e.g., directives/_rules/rules.merged.md)"),
    until_end: bool = typer.Option(False, "--until-end", help="Ignore span and continue until the model emits NEXT: [END]"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Prompt to wait for browser capture before starting"),
):
    cli: CLIContext = ctx.obj
    p = Path(book_file)
    if not p.exists():
        typer.echo(f"File not found: {p}")
        raise typer.Exit(1)

    if not subject:
        subject = p.stem.replace(".final", "").replace(".manual.en", "").replace(".outline", "").replace("_", " ").replace("-", " ").strip().title() or "Subject"

    L = LENGTH_PRESETS.get(length.lower())
    if not L:
        typer.echo("Unknown --length. Choose: standard|long|very-long|max")
        raise typer.Exit(2)

    overlays = ["narrative", "no_bs"]
    extra_note = ""
    if profile:
        spec = DEFAULT_PROFILES.get(profile)
        if not spec:
            typer.echo(f"Unknown profile: {profile}")
            raise typer.Exit(2)
        overlays = spec["overlays"]
        extra_note = spec["extra"]

    total_chunks = None if until_end else SPAN_PRESETS.get(span.lower())
    if not until_end and not total_chunks:
        typer.echo("Unknown --span. Choose: medium|long|book")
        raise typer.Exit(2)

    comp = compose_prompt(subject=subject, base="zero2hero", overlays=overlays, extra_notes=extra_note,
                          min_chars=L["min"], passes=L["passes"], max_chunks=(total_chunks or 40))
    system_text = comp.system_text
    for ef in extra_file:
        ep = Path(ef)
        if ep.exists() and ep.is_file():
            try:
                system_text += "\n\n" + ep.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    if wait:
        typer.echo("\nOpen https://lmarena.ai and add '#bridge=8080' (or your port) to the URL.")
        typer.echo("Click 'Retry' on any message to activate the tab.")
        typer.echo("Press ENTER here to begin...")
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    async def _run():
        await _seed_and_continue(cli, p, system_text, init_chunks=total_chunks, min_chars=L["min"], passes=L["passes"])
    asyncio.run(_run())

    typer.echo(f"[continue] done → {p}")