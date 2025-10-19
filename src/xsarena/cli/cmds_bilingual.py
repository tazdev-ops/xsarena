"""CLI commands for the Bilingual mode."""

import asyncio
from pathlib import Path

import typer

from ..modes.bilingual import BilingualMode
from .context import CLIContext

app = typer.Typer(help="Bilingual text processing tools")


@app.command("transform")
def bilingual_transform(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to translate"),
    source_lang: str = typer.Option(
        "English", "--source", "-s", help="Source language"
    ),
    target_lang: str = typer.Option(
        "Spanish", "--target", "-t", help="Target language"
    ),
):
    """Translate text from source language to target language."""
    cli: CLIContext = ctx.obj
    mode = BilingualMode(cli.engine)

    async def run():
        result = await mode.transform(text, source_lang, target_lang)
        typer.echo(result)

    asyncio.run(run())


@app.command("check")
def bilingual_check(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to source text file"),
    translated_file: str = typer.Argument(..., help="Path to translated text file"),
    source_lang: str = typer.Option(
        "English", "--source", "-s", help="Source language"
    ),
    target_lang: str = typer.Option(
        "Spanish", "--target", "-t", help="Target language"
    ),
):
    """Check alignment between source and translated text."""
    cli: CLIContext = ctx.obj
    mode = BilingualMode(cli.engine)

    source_text = Path(source_file).read_text(encoding="utf-8")
    translated_text = Path(translated_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.alignment_check(
            source_text, translated_text, source_lang, target_lang
        )
        typer.echo(result)

    asyncio.run(run())


@app.command("improve")
def bilingual_improve(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to source text file"),
    current_translation_file: str = typer.Argument(
        ..., help="Path to current translation file"
    ),
    source_lang: str = typer.Option(
        "English", "--source", "-s", help="Source language"
    ),
    target_lang: str = typer.Option(
        "Spanish", "--target", "-t", help="Target language"
    ),
):
    """Improve an existing translation."""
    cli: CLIContext = ctx.obj
    mode = BilingualMode(cli.engine)

    source_text = Path(source_file).read_text(encoding="utf-8")
    current_translation = Path(current_translation_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.improve_translation(
            source_text, current_translation, source_lang, target_lang
        )
        typer.echo(result)

    asyncio.run(run())


@app.command("glossary")
def bilingual_glossary(
    ctx: typer.Context,
    text_file: str = typer.Argument(
        ..., help="Path to text file for glossary building"
    ),
    source_lang: str = typer.Option(
        "English", "--source", "-s", help="Source language"
    ),
    target_lang: str = typer.Option(
        "Spanish", "--target", "-t", help="Target language"
    ),
):
    """Build a glossary of key terms from bilingual text."""
    cli: CLIContext = ctx.obj
    mode = BilingualMode(cli.engine)

    text = Path(text_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.glossary_build(text, source_lang, target_lang)
        typer.echo(result)

    asyncio.run(run())
