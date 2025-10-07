#!/usr/bin/env python3
import pathlib
import shutil
import subprocess

import typer

app = typer.Typer(help="Import files (PDF/DOCX/MD) into sources/ as Markdown")


def _slug(s: str) -> str:
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "doc"


def _to_md(input_path: pathlib.Path) -> str:
    # try pypandoc, else shell pandoc, else raw read if .md
    try:
        import pypandoc  # type: ignore

        return pypandoc.convert_file(str(input_path), "md")
    except Exception:
        if shutil.which("pandoc"):
            cmd = ["pandoc", str(input_path), "-t", "gfm"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout
        if input_path.suffix.lower() == ".md":
            return input_path.read_text(encoding="utf-8")
        raise RuntimeError("No converter found; install pandoc or pypandoc")


@app.command("run")
def import_run(
    file: str, subject: str = typer.Option("imported", "--subject"), dest_dir: str = typer.Option("sources", "--dest")
):
    p = pathlib.Path(file)
    if not p.exists():
        raise typer.Exit(code=2)
    md = _to_md(p)
    sub_slug = _slug(subject)
    outdir = pathlib.Path(dest_dir) / sub_slug
    outdir.mkdir(parents=True, exist_ok=True)
    outf = outdir / (p.stem + ".md")
    outf.write_text(md, encoding="utf-8")
    typer.echo(f"[import] Wrote {outf}")
    typer.echo("To build a synthesis:")
    typer.echo(f"/ingest.synth {outf} books/{sub_slug}.synth.md 100 16000")
