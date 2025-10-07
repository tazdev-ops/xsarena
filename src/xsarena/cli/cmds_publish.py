#!/usr/bin/env python3
import json
import pathlib
import shutil
import subprocess
import sys

import typer

app = typer.Typer(help="Publish artifacts (EPUB/PDF) from a job or a markdown file.")


def _jobs_root():
    return pathlib.Path(".xsarena") / "jobs"


def _books_root():
    return pathlib.Path("books")


def _slugify(s: str) -> str:
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "book"


def _find_final_for_job(jid: str) -> pathlib.Path | None:
    # prefer books/<slug>.final.md; fallback to books/<slug>.manual.en.md
    job_json = _jobs_root() / jid / "job.json"
    if not job_json.exists():
        return None
    try:
        J = json.loads(job_json.read_text(encoding="utf-8"))
        subject = J.get("params", {}).get("subject") or J.get("playbook", {}).get("subject") or "book"
        slug = _slugify(subject)
        p1 = _books_root() / f"{slug}.final.md"
        p2 = _books_root() / f"{slug}.manual.en.md"
        if p1.exists():
            return p1
        if p2.exists():
            return p2
    except Exception:
        return None
    return None


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")
    return proc.returncode


@app.command("run")
def publish(
    target: str = typer.Argument(..., help="<job_id> or path to markdown"),
    epub: bool = typer.Option(True, "--epub/--no-epub", help="Produce .epub"),
    pdf: bool = typer.Option(False, "--pdf/--no-pdf", help="Produce .pdf (requires pandoc + LaTeX)"),
    title: str = typer.Option(None, "--title", help="Override title metadata"),
    toc: bool = typer.Option(True, "--toc/--no-toc", help="With table of contents"),
):
    """
    Publish artifacts (EPUB/PDF) from a job or a markdown file.
    After EPUB export, you can generate audiobooks with: xsarena audio run <job_id>
    """
    pandoc = shutil.which("pandoc")
    if not pandoc:
        typer.echo("Pandoc not found. Install pandoc to use 'xsarena publish'.", err=True)
        raise typer.Exit(2)

    # Determine input markdown file
    md = None
    p = pathlib.Path(target)
    if p.exists() and p.suffix.lower() == ".md":
        md = p
        subj_slug = p.stem
    else:
        # treat as job_id
        md = _find_final_for_job(target)
        if not md:
            typer.echo(f"Could not find final markdown for job: {target}", err=True)
            raise typer.Exit(1)
        subj_slug = md.stem.replace(".final", "")

    typer.echo(f"[publish] Input: {md}")

    # Outputs
    out_epub = _books_root() / f"{subj_slug}.epub"
    out_pdf = _books_root() / f"{subj_slug}.pdf"

    # Common args
    cmd_base = [pandoc, str(md)]
    if title:
        cmd_base += ["-M", f"title={title}"]
    if toc:
        cmd_base += ["--toc"]
    cmd_base += ["-V", "mainfont=DejaVu Serif"]

    # add citeproc if bibliography present
    proj_bib = pathlib.Path(".xsarena") / "project.yml"
    bib = None
    csl = None
    try:
        import yaml

        cfg = yaml.safe_load(proj_bib.read_text(encoding="utf-8")) if proj_bib.exists() else {}
        bib = cfg.get("publish", {}).get("bibliography")
        csl = cfg.get("publish", {}).get("csl")
    except Exception:
        pass
    if bib and pathlib.Path(bib).exists():
        cmd_base += ["--citeproc", "--bibliography", str(bib)]
        if csl and pathlib.Path(csl).exists():
            cmd_base += ["--csl", str(csl)]

    # add theme CSS if found
    theme_css = pathlib.Path("directives") / "theme.epub.css"
    if theme_css.exists():
        cmd_base += ["-c", str(theme_css)]

    # EPUB
    if epub:
        cmd = cmd_base + ["-o", str(out_epub)]
        typer.echo(f"[publish] EPUB → {out_epub}")
        rc = _run(cmd)
        if rc != 0:
            typer.echo("EPUB generation failed.", err=True)

    # PDF
    if pdf:
        # Prefer xelatex if available; else let pandoc pick default
        pdf_engine = None
        for eng in ("xelatex", "pdflatex", "lualatex"):
            if shutil.which(eng):
                pdf_engine = eng
                break
        cmd = cmd_base[:]
        if pdf_engine:
            cmd += ["--pdf-engine", pdf_engine]
        cmd += ["-o", str(out_pdf)]
        typer.echo(f"[publish] PDF → {out_pdf}")
        rc = _run(cmd)
        if rc != 0:
            typer.echo("PDF generation failed.", err=True)

    # Mention audio generation capability after EPUB export
    if epub:
        typer.echo("[publish] To generate audiobook from EPUB: xsarena audio run <job_id> --provider edge")

    typer.echo("[publish] Done.")
