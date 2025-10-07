#!/usr/bin/env python3
import pathlib
import re
import shutil
import subprocess

import typer

app = typer.Typer(help="Generate diagrams from Mermaid code blocks")


@app.command("run")
def diagrams_run(input_md: str, outdir: str = "./images", engine: str = "mmdc"):
    p = pathlib.Path(input_md)
    text = p.read_text(encoding="utf-8")
    blocks = list(re.finditer(r"```mermaid\s+(.+?)\s+```", text, re.DOTALL))
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for i, m in enumerate(blocks, start=1):
        code = m.group(1)
        svg_path = out / f"diagram_{i:03d}.svg"
        if engine == "mmdc" and shutil.which("mmdc"):
            # requires mermaid-cli
            tmp = out / f"diagram_{i:03d}.mmd"
            tmp.write_text(code, encoding="utf-8")
            subprocess.run(["mmdc", "-i", str(tmp), "-o", str(svg_path)], check=False)
            count += 1
        else:
            # fallback: print code; user can decide how to render
            (out / f"diagram_{i:03d}.mmd").write_text(code, encoding="utf-8")
            count += 1
    typer.echo(f"[diagram] processed {count} blocks → {outdir}")
