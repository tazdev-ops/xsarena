#!/usr/bin/env python3
import pathlib

import typer

app = typer.Typer(help="Initialize projects and manage templates")


@app.command("project")
def init_project():
    root = pathlib.Path(".")
    for d in ("books", "directives", "playbooks", "sources", "recipes", ".xsarena"):
        (root / d).mkdir(parents=True, exist_ok=True)
    proj = root / ".xsarena" / "project.yml"
    if not proj.exists():
        proj.write_text(
            "backend: bridge\nmodel: null\ncontinuation:\n  mode: anchor\n  minChars: 3000\n  pushPasses: 1\n  repeatWarn: true\nfailover:\n  watchdog_secs: 45\n  max_retries: 3\n  fallback_backend: openrouter\nstyle:\n  nobs: true\n  narrative: true\n",
            encoding="utf-8",
        )
    pb = root / "playbooks" / "z2h.yml"
    if not pb.exists():
        pb.write_text(
            'name: "Zero-to-Hero"\nversion: "1.0"\ntask: book.zero2hero\nsubject: "{{subject}}"\nstyles: [narrative]\nsystem_text: "Write in pedagogical style with teach-before-use, quick checks, and pitfalls."\nprelude:\n  - "/style.narrative on"\n  - "/cont.mode anchor"\n  - "/out.minchars 3000"\nio:\n  output: file\n  outPath: "./books/{{subject_slug}}.md"\nmax_chunks: 8\n',
            encoding="utf-8",
        )
    typer.echo("[init] Project scaffolded.")
